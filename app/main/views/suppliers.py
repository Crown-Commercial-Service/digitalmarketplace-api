from datetime import datetime
from flask import jsonify, abort, request, current_app
from sqlalchemy.exc import IntegrityError, DataError
from .. import main
from ... import db
from ...models import (
    Supplier, ContactInformation, AuditEvent,
    Service, SupplierFramework, Framework, User,
    FrameworkAgreement
)
from ...validation import (
    validate_supplier_json_or_400,
    validate_contact_information_json_or_400,
    is_valid_string_or_400
)
from ...utils import (
    pagination_links,
    drop_foreign_fields,
    get_json_from_request,
    json_has_required_keys,
    json_only_has_required_keys,
    json_has_matching_id,
    get_valid_page_or_1,
    validate_and_return_updater_request,
)
from ...supplier_utils import validate_and_return_supplier_request, validate_agreement_details_data
from dmapiclient.audit import AuditTypes
from dmutils.formats import DATETIME_FORMAT


@main.route('/suppliers', methods=['GET'])
def list_suppliers():
    page = get_valid_page_or_1()

    prefix = request.args.get('prefix', '')

    framework = request.args.get('framework')

    duns_number = request.args.get('duns_number')

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

    if duns_number:
        is_valid_string_or_400(duns_number)
        suppliers = suppliers.filter(
            Supplier.duns_number == duns_number
        )

    if prefix:
        if prefix == 'other':
            suppliers = suppliers.filter(
                Supplier.name.op('~')('^[^A-Za-z]'))
        else:
            # case insensitive LIKE comparison for matching supplier names
            suppliers = suppliers.filter(
                Supplier.name.ilike(prefix + '%'))

    suppliers = suppliers.distinct(Supplier.name, Supplier.supplier_id)

    try:
        suppliers = suppliers.paginate(
            page=page,
            per_page=current_app.config['DM_API_SUPPLIERS_PAGE_SIZE'],
        )

        return jsonify(
            suppliers=[supplier.serialize() for supplier in suppliers.items],
            links=pagination_links(
                suppliers,
                '.list_suppliers',
                request.args
            ))
    except DataError:
        abort(400, 'invalid framework')


@main.route('/suppliers/<int:supplier_id>', methods=['GET'])
def get_supplier(supplier_id):
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    service_counts = supplier.get_service_counts()

    return jsonify(suppliers=supplier.serialize({
        'service_counts': service_counts
    }))


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
        abort(400, "Database Error: {0}".format(e))

    return jsonify(suppliers=supplier.serialize()), 201


@main.route('/suppliers', methods=['POST'])
def create_supplier():
    supplier_data = validate_and_return_supplier_request()

    contact_informations_data = supplier_data['contactInformation']
    supplier_data = drop_foreign_fields(
        supplier_data,
        ['contactInformation']
    )

    supplier = Supplier()
    supplier.update_from_json(supplier_data)

    for contact_information_data in contact_informations_data:
        contact_information = ContactInformation.from_json(contact_information_data)
        supplier.contact_information.append(contact_information)

    try:
        db.session.add(supplier)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify(message="Database Error: {0}".format(e)), 400

    return jsonify(suppliers=supplier.serialize()), 201


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
            data={'update': request_data['suppliers']})
    )

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(suppliers=supplier.serialize())


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
            data={'update': request_data['contactInformation']})
    )

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(contactInformation=contact.serialize())


@main.route('/suppliers/<supplier_id>/frameworks/<framework_slug>/declaration', methods=['PUT'])
def set_a_declaration(supplier_id, framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier_framework = SupplierFramework.find_by_supplier_and_framework(
        supplier_id, framework_slug
    )
    if supplier_framework is not None:
        status_code = 200 if supplier_framework.declaration else 201
    else:
        supplier = Supplier.query.filter(
            Supplier.supplier_id == supplier_id
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

    supplier_framework.declaration = request_data['declaration'] or {}
    db.session.add(supplier_framework)
    db.session.add(
        AuditEvent(
            audit_type=AuditTypes.answer_selection_questions,
            db_object=supplier_framework,
            user=updater_json['updated_by'],
            data={'update': request_data['declaration']})
    )

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {}".format(e))

    return jsonify(declaration=supplier_framework.declaration), status_code


@main.route('/suppliers/<supplier_id>/frameworks/interest', methods=['GET'])
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

    return jsonify(frameworks=slugs)


@main.route('/suppliers/<supplier_id>/frameworks', methods=['GET'])
def get_supplier_frameworks_info(supplier_id):
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    service_counts = SupplierFramework.get_service_counts(supplier_id)

    supplier_frameworks = SupplierFramework.query.filter(
        SupplierFramework.supplier == supplier
    ).all()

    return jsonify(frameworkInterest=[
        framework.serialize({
            'drafts_count': service_counts.get((framework.framework_id, 'not-submitted'), 0),
            'complete_drafts_count': service_counts.get((framework.framework_id, 'submitted'), 0),
            'services_count': service_counts.get((framework.framework_id, 'published'), 0)
        })
        for framework in supplier_frameworks]
    )


@main.route('/suppliers/<supplier_id>/frameworks/<framework_slug>', methods=['GET'])
def get_supplier_framework_info(supplier_id, framework_slug):
    supplier_framework = SupplierFramework.find_by_supplier_and_framework(
        supplier_id, framework_slug
    )
    if supplier_framework is None:
        abort(404)

    return jsonify(frameworkInterest=supplier_framework.serialize())


@main.route('/suppliers/<supplier_id>/frameworks/<framework_slug>', methods=['PUT'])
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
        return jsonify(frameworkInterest=interest_record.serialize()), 200

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
        return jsonify(message="Database Error: {0}".format(e)), 400

    return jsonify(frameworkInterest=interest_record.serialize()), 201


@main.route('/suppliers/<supplier_id>/frameworks/<framework_slug>', methods=['POST'])
def update_supplier_on_framework(supplier_id, framework_slug):
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
    json_only_has_required_keys(update_json, ["onFramework"])

    interest_record = SupplierFramework.query.filter(
        SupplierFramework.supplier_id == supplier.supplier_id,
        SupplierFramework.framework_id == framework.id
    ).first()

    if not interest_record:
        abort(404, "supplier_id '{}' has not registered interest in {}".format(supplier_id, framework_slug))

    interest_record.on_framework = update_json['onFramework']

    audit_event = AuditEvent(
        audit_type=AuditTypes.supplier_update,
        user=updater_json['updated_by'],
        data={'supplierId': supplier.supplier_id, 'frameworkSlug': framework_slug, 'update': update_json},
        db_object=supplier
    )

    try:
        db.session.add(interest_record)
        db.session.add(audit_event)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify(message="Database Error: {0}".format(e)), 400

    return jsonify(frameworkInterest=interest_record.serialize()), 200


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
        return jsonify(message="Database Error: {0}".format(e)), 400

    return jsonify(
        agreedVariations=SupplierFramework.serialize_agreed_variation(agreed_variations[variation_slug]),
    ), 200
