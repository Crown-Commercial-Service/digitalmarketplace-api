from flask import jsonify, abort, request, current_app
from sqlalchemy.exc import IntegrityError, DataError
from .. import main
from ... import db
from ...models import Supplier, ContactInformation, AuditEvent, Service, SupplierFramework, Framework
from ...validation import (
    validate_supplier_json_or_400,
    validate_contact_information_json_or_400,
    is_valid_string_or_400
)
from ...utils import pagination_links, drop_foreign_fields, get_json_from_request, \
    json_has_required_keys, json_has_matching_id, get_valid_page_or_1
from ...service_utils import validate_and_return_updater_request
from ...supplier_utils import validate_and_return_supplier_request
from dmutils.audit import AuditTypes


@main.route('/suppliers', methods=['GET'])
def list_suppliers():
    page = get_valid_page_or_1()

    prefix = request.args.get('prefix', '')

    framework = request.args.get('framework')

    duns_number = request.args.get('duns_number')

    if framework:
        is_valid_string_or_400(framework)

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

    json_has_required_keys(
        request_data,
        ['suppliers', 'updated_by']
    )

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
            user=request_data['updated_by'],
            data={'update': request_data['suppliers']})
    )

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(suppliers=supplier.serialize())


@main.route(
    '/suppliers/<int:supplier_id>/contact-information/<int:contact_id>',
    methods=['POST'])
def update_contact_information(supplier_id, contact_id):
    request_data = get_json_from_request()

    contact = ContactInformation.query.filter(
        ContactInformation.id == contact_id,
        ContactInformation.supplier_id == supplier_id,
    ).first_or_404()

    json_has_required_keys(request_data, [
        'contactInformation', 'updated_by'
    ])

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
            user=request_data['updated_by'],
            data={'update': request_data['contactInformation']})
    )

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(contactInformation=contact.serialize())


# TODO: deprecated - remove route once all frontend apps are using utils version 10.8.0 or higher
@main.route('/suppliers/<supplier_id>/frameworks/<framework_slug>/declaration', methods=['GET'])
def get_a_declaration(supplier_id, framework_slug):
    current_app.logger.warning("Deprecated /suppliers/<supplier_id>/frameworks/<framework_slug>/declaration route")
    supplier_framework = SupplierFramework.find_by_supplier_and_framework(
        supplier_id, framework_slug
    )
    if supplier_framework is None:
        abort(404)

    return jsonify(declaration=supplier_framework.declaration)


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
    json_has_required_keys(request_data, ['declaration', 'updated_by'])

    supplier_framework.declaration = request_data['declaration']
    db.session.add(supplier_framework)
    db.session.add(
        AuditEvent(
            audit_type=AuditTypes.answer_selection_questions,
            db_object=supplier_framework,
            user=request_data['updated_by'],
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


@main.route('/suppliers/<supplier_id>/frameworks/<framework_slug>', methods=['GET'])
def get_supplier_framework_info(supplier_id, framework_slug):
    supplier_framework = SupplierFramework.find_by_supplier_and_framework(
        supplier_id, framework_slug
    )
    if supplier_framework is None:
        abort(404)

    return jsonify(frameworkInterest=supplier_framework.serialize())


# TODO: deprecated - remove route once all frontend apps are using utils version 10.8.0 or higher
@main.route('/suppliers/<supplier_id>/frameworks/<framework_slug>/interest', methods=['POST'])
def register_interest_in_framework(supplier_id, framework_slug):
    current_app.logger.warning("Deprecated /suppliers/<supplier_id>/frameworks/<framework_slug>/interest route")
    updater_json = validate_and_return_updater_request()

    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    if framework.status != 'open':
        abort(400, "'{}' framework is not open".format(framework_slug))

    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    interest_record = SupplierFramework.query.filter(
        SupplierFramework.supplier_id == supplier_id,
        SupplierFramework.framework_id == framework.id
    ).first()

    if interest_record:
        return jsonify(frameworkInterest=interest_record.serialize()), 200
    else:
        interest_record = SupplierFramework(
            supplier_id=supplier_id,
            framework_id=framework.id
        )
        audit_event = AuditEvent(
            audit_type=AuditTypes.register_framework_interest,
            user=updater_json.get('user'),
            data={'supplierId': supplier_id, 'frameworkSlug': framework_slug},
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


@main.route('/suppliers/<supplier_id>/frameworks/<framework_slug>', methods=['PUT'])
def register_framework_interest(supplier_id, framework_slug):
    updater_json = validate_and_return_updater_request()

    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    interest_record = SupplierFramework.query.filter(
        SupplierFramework.supplier_id == supplier_id,
        SupplierFramework.framework_id == framework.id
    ).first()

    json_payload = get_json_from_request()
    json_payload.pop('update_details')
    if json_payload:
        abort(400, "This PUT endpoint does not take a payload.")

    if interest_record:
        return jsonify(frameworkInterest=interest_record.serialize()), 200

    if framework.status != 'open':
        abort(400, "'{}' framework is not open".format(framework_slug))

    interest_record = SupplierFramework(
        supplier_id=supplier_id,
        framework_id=framework.id
    )
    audit_event = AuditEvent(
        audit_type=AuditTypes.register_framework_interest,
        user=updater_json.get('updated_by'),
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
def update_supplier_framework_details(supplier_id, framework_slug):
    updater_json = validate_and_return_updater_request()

    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["frameworkInterest"])
    update_json = json_payload["frameworkInterest"]

    interest_record = SupplierFramework.query.filter(
        SupplierFramework.supplier_id == supplier_id,
        SupplierFramework.framework_id == framework.id
    ).first()

    if not interest_record:
        abort(404, "supplier_id '{}' has not registered interest in {}".format(supplier_id, framework_slug))

    if 'onFramework' in update_json:
        interest_record.on_framework = update_json['onFramework']
        if interest_record.on_framework is True and interest_record.agreement_returned is None:
            interest_record.agreement_returned = False
    if 'agreementReturned' in update_json:
        interest_record.agreement_returned = update_json['agreementReturned']

    audit_event = AuditEvent(
        audit_type=AuditTypes.supplier_update,
        user=updater_json.get('updated_by'),
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
