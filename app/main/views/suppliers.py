from datetime import datetime

from flask import jsonify, abort, request, current_app
from itertools import groupby
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.sql.expression import or_ as sql_or
from sqlalchemy.orm import lazyload
from sqlalchemy.orm.exc import NoResultFound
from dmapiclient.audit import AuditTypes
from dmutils.formats import DATETIME_FORMAT

from .. import main
from ... import db
from ...supplier_utils import (
    company_details_confirmed_if_required_for_framework,
    update_open_declarations_with_company_details,
)
from ...models import Supplier, ContactInformation, AuditEvent, Service, SupplierFramework, Framework, User
from ...validation import (
    is_valid_string_or_400,
    validate_contact_information_json_or_400,
    validate_supplier_json_or_400,
)
from ...utils import (
    drop_foreign_fields,
    get_json_from_request,
    get_valid_page_or_1,
    json_has_keys,
    json_has_matching_id,
    json_has_required_keys,
    json_only_has_required_keys,
    paginated_result_response,
    single_result_response,
    validate_and_return_updater_request,
)
from ...supplier_utils import validate_and_return_supplier_request

RESOURCE_NAME = "suppliers"


@main.route('/suppliers', methods=['GET'])
def list_suppliers():
    page = get_valid_page_or_1()

    prefix = request.args.get('prefix', '')

    name = request.args.get('name', '')

    framework = request.args.get('framework')

    duns_number = request.args.get('duns_number')

    company_registration_number = request.args.get('company_registration_number')

    if framework:
        is_valid_string_or_400(framework)

        # TODO: remove backwards compatibility
        if framework == 'gcloud':
            framework = 'g-cloud'

        suppliers = Supplier.query.join(
            Service.supplier, Service.framework
        ).filter(
            Framework.status == 'live',
            Framework.framework == framework,
            Service.status == 'published'
        ).order_by(Supplier.name, Supplier.supplier_id)
    else:
        suppliers = Supplier.query.order_by(Supplier.name, Supplier.supplier_id)

    # Can search by either DUNS or Company Registration number but not both
    if duns_number:
        is_valid_string_or_400(duns_number)
        suppliers = suppliers.filter(
            Supplier.duns_number == duns_number
        )
    elif company_registration_number:
        is_valid_string_or_400(company_registration_number)
        # For now we only need to search by Companies House number, not overseas registration numbers
        suppliers = suppliers.filter(
            Supplier.companies_house_number == company_registration_number
        )

    if prefix:
        if prefix == 'other':
            suppliers = suppliers.filter(
                Supplier.name.op('~')('^[^A-Za-z]'))
        else:
            # case insensitive LIKE comparison for matching supplier names
            suppliers = suppliers.filter(Supplier.name.ilike(prefix + '%'))

    if name:
        # case insensitive LIKE comparison for matching supplier names and registered names
        suppliers = suppliers.filter(
            sql_or(
                Supplier.name.ilike('%{}%'.format(name)),
                Supplier.registered_name.ilike('%{}%'.format(name))
            )
        )

    suppliers = suppliers.distinct(Supplier.name, Supplier.supplier_id)

    try:
        return paginated_result_response(
            result_name=RESOURCE_NAME,
            results_query=suppliers,
            page=page,
            per_page=current_app.config['DM_API_SUPPLIERS_PAGE_SIZE'],
            endpoint='.list_suppliers',
            request_args=request.args
        ), 200
    except DataError:
        abort(400, 'invalid framework')


@main.route('/suppliers/export/<framework_slug>', methods=['GET'])
def export_suppliers_for_framework(framework_slug):
    # 400 if framework slug is invalid
    framework = Framework.query.filter(Framework.slug == framework_slug).first()
    if not framework:
        abort(400, 'invalid framework')

    if framework.status == 'coming':
        abort(400, 'framework not yet open')

    lot_slugs_by_id = {lot.id: lot.slug for lot in framework.lots}

    # Creates a dictionary of dictionaries, with published service counts per lot per supplier.
    # To do this we use dictionary comprehension, SQL query and itertools' 'groupby' function.
    # Grouping by supplier id is more efficient as this is what we will be iterating over later.
    service_counts_by_lot_by_supplier = {
        supplier_id: {row[1]: row[2] for row in rows}
        for supplier_id, rows in groupby(
            db.session.query(
                Service.supplier_id,
                Service.lot_id,
                func.count(Service.id)
            ).filter(
                Service.status == 'published',
                Service.framework_id == framework.id
            ).order_by(
                Service.supplier_id,
                Service.lot_id,
            ).group_by(
                Service.supplier_id,
                Service.lot_id,
            ).all(),
            key=lambda row: row[0],
        )
    }

    suppliers_and_framework = db.session.query(
        SupplierFramework, Supplier, ContactInformation
    ).filter(
        SupplierFramework.supplier_id == Supplier.supplier_id
    ).filter(
        SupplierFramework.framework_id == framework.id
    ).filter(
        ContactInformation.supplier_id == Supplier.supplier_id
    ).options(
        lazyload(SupplierFramework.framework),
        lazyload(SupplierFramework.prefill_declaration_from_framework),
        lazyload(SupplierFramework.framework_agreements),
    ).order_by(
        Supplier.supplier_id
    ).all()

    supplier_rows = []

    suppliers_with_a_complete_service = frozenset(framework.get_supplier_ids_for_completed_service())

    for sf, supplier, ci in suppliers_and_framework:
        declaration_status = sf.declaration.get('status') if sf.declaration else 'unstarted'

        # This `application_status` logic also exists in users.export_users_for_framework
        application_status = 'application' if (
            declaration_status == 'complete' and
            supplier.supplier_id in suppliers_with_a_complete_service and
            company_details_confirmed_if_required_for_framework(framework_slug, sf)
        ) else 'no_application'

        application_result = ''
        framework_agreement = False
        variations_agreed = ''

        if framework.status != 'open':
            if sf.on_framework is None:
                application_result = 'no result'
            else:
                application_result = 'pass' if sf.on_framework else 'fail'
            framework_agreement = bool(getattr(sf.current_framework_agreement, 'signed_agreement_returned_at', None))
            variations_agreed = ', '.join(sf.agreed_variations.keys()) if sf.agreed_variations else ''

        supplier_rows.append({
            "supplier_id": supplier.supplier_id,
            "supplier_name": supplier.name,
            "supplier_organisation_size": supplier.organisation_size,
            "duns_number": supplier.duns_number,
            "registered_name": supplier.registered_name,
            "companies_house_number": supplier.companies_house_number,
            "other_company_registration_number": supplier.other_company_registration_number,
            'application_result': application_result,
            'application_status': application_status,
            'declaration_status': declaration_status,
            'framework_agreement': framework_agreement,
            'variations_agreed': variations_agreed,
            "published_services_count": {
                lot_slugs_by_id[lot_id]: service_counts_by_lot_by_supplier.get(
                    supplier.supplier_id, {}
                ).get(lot_id, 0)
                for lot_id in lot_slugs_by_id.keys()
            },
            "contact_information": {
                'contact_name': ci.contact_name,
                'contact_email': ci.email,
                'contact_phone_number': ci.phone_number,
                'address_first_line': ci.address1,
                'address_city': ci.city,
                'address_postcode': ci.postcode,
                'address_country': supplier.registration_country,
            }
        })

    return jsonify(suppliers=supplier_rows), 200


@main.route('/suppliers/<int:supplier_id>', methods=['GET'])
def get_supplier(supplier_id):
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    service_counts = supplier.get_service_counts()

    return single_result_response(
        RESOURCE_NAME,
        supplier,
        serialize_kwargs={"data": {"service_counts": service_counts}}
    ), 200


@main.route('/suppliers/<int:supplier_id>', methods=['PUT'])
def import_supplier(supplier_id):
    supplier_data = validate_and_return_supplier_request(supplier_id)

    contact_informations_data = supplier_data['contactInformation']
    supplier_data = drop_foreign_fields(
        supplier_data,
        ['contactInformation']
    )

    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_data['id']
    ).first()

    if supplier is None:
        supplier = Supplier(supplier_id=supplier_data['id'])

    # if a supplier was found, remove all contact information
    else:
        for contact in supplier.contact_information:
            db.session.delete(contact)

    supplier.update_from_json(supplier_data)

    for contact_information_data in contact_informations_data:
        contact_information = ContactInformation.from_json(contact_information_data)
        supplier.contact_information.append(contact_information)

        db.session.add(supplier)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, supplier), 201


@main.route('/suppliers', methods=['POST'])
def create_supplier():
    request_data = validate_and_return_supplier_request()

    contact_informations_data = request_data['contactInformation']
    supplier_data = drop_foreign_fields(
        request_data.copy(),
        ['contactInformation']
    )

    supplier = Supplier()
    supplier.update_from_json(supplier_data)

    for contact_information_data in contact_informations_data:
        contact_information = ContactInformation.from_json(contact_information_data)
        supplier.contact_information.append(contact_information)

    try:
        db.session.add(supplier)
        db.session.flush()  # flush so the supplier object gets an ID and can be properly attached to the AuditEvent

        db.session.add(
            AuditEvent(
                audit_type=AuditTypes.create_supplier,
                db_object=supplier,
                user="no logged-in user",
                data={
                    "update": request_data,
                    "supplierId": supplier.supplier_id,
                },
            )
        )
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, supplier), 201


@main.route('/suppliers/<int:supplier_id>', methods=['POST'])
def update_supplier(supplier_id):
    request_data = get_json_from_request()

    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    updater_json = validate_and_return_updater_request()
    json_has_required_keys(request_data, ['suppliers'])

    supplier_data = supplier.serialize()
    supplier_data.update(request_data['suppliers'])
    supplier_data = drop_foreign_fields(
        supplier_data,
        ['links', 'contactInformation']
    )

    validate_supplier_json_or_400(supplier_data)
    json_has_matching_id(supplier_data, supplier_id)

    supplier.update_from_json(supplier_data)

    db.session.add(supplier)
    db.session.add(
        AuditEvent(
            audit_type=AuditTypes.supplier_update,
            db_object=supplier,
            user=updater_json['updated_by'],
            data={
                "update": request_data["suppliers"],
                "supplierId": supplier.supplier_id,
            },
        )
    )

    update_open_declarations_with_company_details(db, supplier_id, updater_json)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, supplier), 200


@main.route('/suppliers/<int:supplier_id>/contact-information/<int:contact_id>', methods=['POST'])
def update_contact_information(supplier_id, contact_id):
    request_data = get_json_from_request()

    contact = ContactInformation.query.filter(
        ContactInformation.id == contact_id,
        ContactInformation.supplier_id == supplier_id,
    ).first_or_404()

    updater_json = validate_and_return_updater_request()
    json_has_required_keys(request_data, ['contactInformation'])
    contact_data = contact.serialize()
    contact_data.update(request_data['contactInformation'])
    contact_data = drop_foreign_fields(
        contact_data,
        ['links']
    )

    validate_contact_information_json_or_400(contact_data)
    json_has_matching_id(contact_data, contact_id)

    contact.update_from_json(contact_data)

    db.session.add(contact)
    db.session.add(
        AuditEvent(
            audit_type=AuditTypes.contact_update,
            db_object=contact.supplier,
            user=updater_json['updated_by'],
            data={
                "update": request_data["contactInformation"],
                "supplierId": contact.supplier.supplier_id,
            },
        )
    )

    update_open_declarations_with_company_details(db, supplier_id, updater_json)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response("contactInformation", contact), 200


@main.route('/suppliers/<int:supplier_id>/contact-information/<int:contact_id>/remove-personal-data', methods=['POST'])
def remove_contact_information_personal_data(supplier_id, contact_id):
    """Remove personal data from a contact information entry. Looks contact information up in DB, and removes personal
    data.

    This should be used to completely remove contact_information from the Marketplace.
    This is useful for our retention strategy (3 years) and for right to be forgotten requests.
    """
    updater_json = validate_and_return_updater_request()

    contact_information = ContactInformation.query.filter(
        ContactInformation.supplier_id == supplier_id,
        ContactInformation.id == contact_id
    ).first_or_404()
    contact_information.remove_personal_data()

    audit = AuditEvent(
        audit_type=AuditTypes.contact_update,
        user=updater_json['updated_by'],
        db_object=contact_information.supplier,
        data={}
    )

    db.session.add(contact_information)
    db.session.add(audit)

    try:
        db.session.commit()
    except (IntegrityError, DataError):
        db.session.rollback()
        error_msg = "Could not remove personal data from contact information: supplier_id {}, id {}"
        abort(400, error_msg.format(supplier_id, contact_id))

    return single_result_response("contactInformation", contact_information), 200


@main.route('/suppliers/<int:supplier_id>/frameworks/<framework_slug>/declaration', methods=["PUT", "PATCH"])
def set_a_declaration(supplier_id, framework_slug):
    supplier_framework = SupplierFramework.find_by_supplier_and_framework(
        supplier_id, framework_slug
    ).options(
        lazyload('*')
    ).with_for_update().first()

    if supplier_framework is not None:
        status_code = 200 if supplier_framework.declaration else 201
    else:
        framework = Framework.query.filter(
            Framework.slug == framework_slug
        ).options(
            lazyload('*')
        ).first_or_404()

        supplier = Supplier.query.filter(
            Supplier.supplier_id == supplier_id
        ).options(
            lazyload('*')
        ).first_or_404()

        supplier_framework = SupplierFramework(
            supplier_id=supplier.supplier_id,
            framework_id=framework.id,
            declaration={}
        )
        status_code = 201

    request_data = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    json_has_required_keys(request_data, ['declaration'])

    if request.method == "PUT" or not supplier_framework.declaration:
        supplier_framework.declaration = request_data['declaration'] or {}
    elif request_data['declaration']:
        supplier_framework.declaration.update(request_data['declaration'])
        # FIXME fix json fields to actually run validators on value mutation - until then the following little absurdity
        # is required, assigning the declaration attr back to itself to ensure validation is performed.
        supplier_framework.declaration = supplier_framework.declaration

    db.session.add(supplier_framework)
    db.session.add(
        AuditEvent(
            audit_type=(
                AuditTypes.answer_selection_questions
                if request.method == "PUT" else
                AuditTypes.update_declaration_answers
            ),
            db_object=supplier_framework,
            user=updater_json['updated_by'],
            data={
                "update": request_data["declaration"],
                "supplierId": supplier_id,
            },
        )
    )

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return jsonify(declaration=supplier_framework.declaration), status_code


@main.route('/suppliers/<int:supplier_id>/frameworks/<framework_slug>/declaration', methods=['POST'])
def remove_a_declaration(framework_slug, supplier_id):
    """
    This route will replace unsuccessful applicants' declarations with an empty dict and returns the updated object,
    serialized in JSON format
    :param framework_slug: a string describing the framework
    :type framework_slug: string
    :param supplier_id: a way of identifying the supplier whose declaration will be removed
    :type supplier_id: int
    :return: The serialized SupplierFramework and a status code
    :rtype: Response
    """
    updater_json = validate_and_return_updater_request()
    supplier_framework = SupplierFramework.find_by_supplier_and_framework(
        supplier_id, framework_slug
    ).first_or_404()

    supplier_framework.declaration = {}

    audit_event = AuditEvent(
        audit_type=AuditTypes.delete_supplier_framework_declaration,
        db_object=supplier_framework,
        user=updater_json['updated_by'],
        data={}
    )

    db.session.add(supplier_framework, audit_event)
    try:
        db.session.commit()
    except (IntegrityError, DataError):
        db.session.rollback()
        error_msg = "Could not remove declaration data from supplier framework: supplier_id {}, framework {}"
        abort(400, error_msg.format(supplier_id, framework_slug))

    return single_result_response("supplierFramework", supplier_framework), 200


@main.route('/suppliers/<int:supplier_id>/frameworks/interest', methods=['GET'])
def get_registered_frameworks(supplier_id):
    supplier_frameworks = SupplierFramework.query.filter(
        SupplierFramework.supplier_id == supplier_id
    ).all()
    slugs = []
    for framework in supplier_frameworks:
        framework = Framework.query.filter(
            Framework.id == framework.framework_id
        ).first()
        slugs.append(framework.slug)

    return jsonify(frameworks=slugs), 200


@main.route('/suppliers/<int:supplier_id>/frameworks', methods=['GET'])
def get_supplier_frameworks_info(supplier_id):
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    service_counts = SupplierFramework.get_service_counts(supplier_id)

    supplier_frameworks = SupplierFramework.query.filter(
        SupplierFramework.supplier == supplier
    ).all()

    return jsonify(frameworkInterest=[
        supplier_framework.serialize({
            'drafts_count': service_counts.get((supplier_framework.framework_id, 'not-submitted'), 0),
            'complete_drafts_count': service_counts.get((supplier_framework.framework_id, 'submitted'), 0),
            'services_count': service_counts.get((supplier_framework.framework_id, 'published'), 0)
        })
        for supplier_framework in supplier_frameworks]
    ), 200


@main.route('/suppliers/<int:supplier_id>/frameworks/<framework_slug>', methods=['GET'])
def get_supplier_framework_info(supplier_id, framework_slug):
    supplier_framework = SupplierFramework.find_by_supplier_and_framework(
        supplier_id, framework_slug
    ).options(
        lazyload('*')
    ).first()

    if supplier_framework is None:
        abort(404)

    return single_result_response(
        "frameworkInterest",
        supplier_framework,
        serialize_kwargs={"with_users": True}
    ), 200


@main.route('/suppliers/<int:supplier_id>/frameworks/<framework_slug>', methods=['PUT'])
def register_framework_interest(supplier_id, framework_slug):

    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    json_payload.pop('updated_by')
    if json_payload:
        abort(400, "This PUT endpoint does not take a payload.")

    interest_record = SupplierFramework.query.filter(
        SupplierFramework.supplier_id == supplier.supplier_id,
        SupplierFramework.framework_id == framework.id
    ).first()
    if interest_record:
        return single_result_response("frameworkInterest", interest_record), 200

    if framework.status != 'open':
        abort(400, "'{}' framework is not open".format(framework_slug))

    interest_record = SupplierFramework(
        supplier_id=supplier.supplier_id,
        framework_id=framework.id,
        declaration={}
    )
    audit_event = AuditEvent(
        audit_type=AuditTypes.register_framework_interest,
        user=updater_json['updated_by'],
        data={'supplierId': supplier.supplier_id, 'frameworkSlug': framework_slug},
        db_object=supplier
    )

    try:
        db.session.add(interest_record)
        db.session.add(audit_event)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response("frameworkInterest", interest_record), 201


@main.route('/suppliers/<int:supplier_id>/frameworks/<framework_slug>', methods=['POST'])
def update_supplier_framework(supplier_id, framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    json_has_required_keys(json_payload, ["frameworkInterest"])
    update_json = json_payload["frameworkInterest"]
    json_has_keys(update_json, optional_keys=(
        "allowDeclarationReuse",
        "applicationCompanyDetailsConfirmed",
        "onFramework",
        "prefillDeclarationFromFrameworkSlug",
    ))

    # fetch and lock SupplierFramework row
    interest_record = SupplierFramework.query.filter(
        SupplierFramework.supplier_id == supplier.supplier_id,
        SupplierFramework.framework_id == framework.id
    ).options(
        lazyload('*')
    ).with_for_update().first()

    if not interest_record:
        abort(404, "supplier_id '{}' has not registered interest in {}".format(supplier_id, framework_slug))

    if "onFramework" in update_json:
        interest_record.on_framework = update_json["onFramework"]

    if "allowDeclarationReuse" in update_json:
        interest_record.allow_declaration_reuse = update_json["allowDeclarationReuse"]

    if "prefillDeclarationFromFrameworkSlug" in update_json:
        if update_json["prefillDeclarationFromFrameworkSlug"] is not None:
            try:
                prefill_declaration_from_framework_id, sf_reuse_allowed, fw_reuse_allowed = db.session.query(
                    SupplierFramework.framework_id,
                    SupplierFramework.allow_declaration_reuse,
                    Framework.allow_declaration_reuse,
                ).join(SupplierFramework.framework).filter(
                    SupplierFramework.framework.has(
                        Framework.slug == update_json["prefillDeclarationFromFrameworkSlug"]
                    ),
                    SupplierFramework.supplier_id == supplier.supplier_id,
                ).one()
            except NoResultFound:
                abort(400, "Supplier hasn't registered interest in a framework with slug '{}'".format(
                    update_json["prefillDeclarationFromFrameworkSlug"]
                ))

            if not sf_reuse_allowed:
                # if we want a stronger guarantee about this remaining correct, we should consider a db constraint
                abort(400, "Supplier's declaration for '{}' not marked as allowDeclarationReuse".format(
                    update_json["prefillDeclarationFromFrameworkSlug"]
                ))

            if not fw_reuse_allowed:
                # if we want a stronger guarantee about this remaining correct, we should consider a db constraint
                abort(400, "Framework with slug '{}' not marked as allowDeclarationReuse".format(
                    update_json["prefillDeclarationFromFrameworkSlug"]
                ))
        else:
            prefill_declaration_from_framework_id = None
        interest_record.prefill_declaration_from_framework_id = prefill_declaration_from_framework_id

    if "applicationCompanyDetailsConfirmed" in update_json:
        interest_record.application_company_details_confirmed = update_json['applicationCompanyDetailsConfirmed']
        if update_json['applicationCompanyDetailsConfirmed'] is True:
            update_open_declarations_with_company_details(db, supplier_id, updater_json,
                                                          specific_framework_slug=framework_slug)

    # The type of this audit event changed from `supplier_update` to `update_supplier_framework` in early June 2018.
    # For an accurate date, check the date this commit went live on the stage you're interested in (probably prod).
    audit_event = AuditEvent(
        audit_type=AuditTypes.update_supplier_framework,
        user=updater_json['updated_by'],
        data={'supplierId': supplier.supplier_id, 'frameworkSlug': framework_slug, 'update': update_json},
        db_object=supplier,
    )

    try:
        db.session.add(interest_record)
        db.session.add(audit_event)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response("frameworkInterest", interest_record), 200


@main.route('/suppliers/<int:supplier_id>/frameworks/<framework_slug>/variation/<variation_slug>', methods=['PUT'])
def agree_framework_variation(supplier_id, framework_slug, variation_slug):

    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    # TODO SELECT FOR UPDATE?
    # (technically we should be doing a FOR UPDATE of SupplierFramework and a FOR SHARE of Framework)
    interest_record = SupplierFramework.query.filter(
        SupplierFramework.supplier_id == supplier.supplier_id,
        SupplierFramework.framework_id == framework.id
    ).first()
    if not interest_record:
        abort(404, "supplier_id '{}' has not registered interest in {}".format(supplier_id, framework_slug))

    if not interest_record.on_framework:
        abort(404, "supplier_id '{}' is not on framework {}".format(supplier_id, framework_slug))

    # acceptable variation_slugs must have corresponding createdAt entry in variations dict
    if not (framework.framework_agreement_details or {}).get("variations", {}).get(variation_slug, {}).get("createdAt"):
        abort(404, "Unknown variation '{}' for framework {}".format(variation_slug, framework_slug))

    if (interest_record.agreed_variations or {}).get(variation_slug, {}).get("agreedAt"):
        abort(400, "supplier_id '{}' has already agreed to variation '{}'.".format(supplier_id, variation_slug))

    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    json_has_required_keys(json_payload, ["agreedVariations"])
    json_only_has_required_keys(json_payload["agreedVariations"], ["agreedUserId"])

    user = User.query.filter(User.id == json_payload["agreedVariations"]["agreedUserId"]).first()
    if not user:
        abort(400, "No user found with id '{}'".format(json_payload["agreedVariations"]["agreedUserId"]))
    if supplier_id != user.supplier_id:
        abort(403, "user '{}' isn't associated with supplier_id '{}'".format(
            json_payload["agreedVariations"]["agreedUserId"],
            supplier_id,
        ))

    agreed_variations = interest_record.agreed_variations.copy() if interest_record.agreed_variations else {}
    agreed_variations[variation_slug] = agreed_variations.get(variation_slug, {})
    agreed_variations[variation_slug].update({
        "agreedAt": datetime.utcnow().strftime(DATETIME_FORMAT),
        "agreedUserId": user.id,
    })
    interest_record.agreed_variations = agreed_variations

    audit_event = AuditEvent(
        audit_type=AuditTypes.agree_framework_variation,
        user=updater_json['updated_by'],
        data={
            'supplierId': supplier.supplier_id,
            'frameworkSlug': framework_slug,
            'variationSlug': variation_slug,
            'update': json_payload["agreedVariations"],
        },
        db_object=interest_record,
    )

    try:
        db.session.add(interest_record)
        db.session.add(audit_event)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return jsonify(
        agreedVariations=SupplierFramework.serialize_agreed_variation(agreed_variations[variation_slug]),
    ), 200
