from datetime import datetime
from flask import jsonify, abort, request, current_app
from elasticsearch import TransportError
from sqlalchemy.exc import IntegrityError, DataError
from .. import main
from ... import db
from ...models import (
    Supplier, AuditEvent,
    Service, SupplierFramework, Framework, PriceSchedule
)
from ...search_indices import es_client, get_supplier_index_name, SUPPLIER_DOC_TYPE, delete_indices, create_indices

from ...validation import (
    validate_supplier_json_or_400,
    validate_contact_information_json_or_400,
    is_valid_string_or_400
)
from ...utils import pagination_links, drop_foreign_fields, get_json_from_request, \
    json_has_required_keys, json_has_matching_id, get_valid_page_or_1, validate_and_return_updater_request
from ...supplier_utils import validate_and_return_supplier_request
from dmapiclient.audit import AuditTypes


@main.route('/suppliers', methods=['GET'])
def list_suppliers():
    page = get_valid_page_or_1()

    prefix = request.args.get('prefix', '')
    name = request.args.get('name', None)

    suppliers = Supplier.query

    if prefix:
        if prefix == 'other':
            suppliers = suppliers.filter(
                Supplier.name.op('~')('^[^A-Za-z]'))
        else:
            # case insensitive LIKE comparison for matching supplier names
            suppliers = suppliers.filter(
                Supplier.name.ilike(prefix + '%'))

    if name is not None:
        suppliers = suppliers.filter((Supplier.name == name) | (Supplier.long_name == name))

    suppliers = suppliers.distinct(Supplier.name, Supplier.code)

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


@main.route('/suppliers/<int:code>', methods=['GET'])
def get_supplier(code):
    supplier = Supplier.query.filter(
        Supplier.code == code
    ).first_or_404()

    service_counts = supplier.get_service_counts()

    return jsonify(supplier=supplier.serialize())


@main.route('/suppliers/<int:code>', methods=['DELETE'])
def delete_supplier(code):
    supplier = Supplier.query.filter(
        Supplier.code == code
    ).first_or_404()

    try:
        result = es_client.delete(index=get_supplier_index_name(),
                                  doc_type=SUPPLIER_DOC_TYPE,
                                  id=supplier.code)
        db.session.delete(supplier)
        db.session.commit()
    except TransportError, e:
        return jsonify(message=str(e)), e.status_code
    except IntegrityError as e:
        db.session.rollback()
        return jsonify(message="Database Error: {0}".format(e)), 400

    return jsonify(message="done"), 200


@main.route('/suppliers', methods=['DELETE'])
def delete_suppliers():
    try:
        Supplier.query.delete()
        db.session.commit()
        delete_indices()
        create_indices()
    except TransportError, e:
        return jsonify(message=str(e)), e.status_code
    except IntegrityError as e:
        db.session.rollback()
        return jsonify(message="Database Error: {0}".format(e)), 400

    return jsonify(message="done"), 200


@main.route('/suppliers/search', methods=['GET'])
def supplier_search():
    try:
        starting_offset = int(request.args.get('from', 0))
        if starting_offset < 0:
            raise ValueError(starting_offset)
    except ValueError, e:
        return jsonify(message="Invalid 'from' value (must be integer > 0): {0}".format(e)), 400

    try:
        result_count = int(request.args.get('size', current_app.config['DM_API_SUPPLIERS_PAGE_SIZE']))
        if result_count < 0:
            raise ValueError(result_count)
    except ValueError, e:
        return jsonify(message="Invalid 'size' value (must be integer > 0): {0}".format(e)), 400

    try:
        result = es_client.search(index=get_supplier_index_name(),
                                  doc_type=SUPPLIER_DOC_TYPE,
                                  body=get_json_from_request(),
                                  from_=starting_offset,
                                  size=result_count)
    except TransportError, e:
        return jsonify(message=str(e)), e.status_code
    except Exception, e:
        return jsonify(message=str(e)), 500

    return jsonify(result), 200


def update_supplier_data_impl(supplier, supplier_data, success_code):
    try:
        import json
        if 'prices' in supplier_data:
            db.session.query(PriceSchedule).filter(PriceSchedule.supplier_id == supplier.id).delete()

        supplier.update_from_json(supplier_data)

        db.session.add(supplier)
        db.session.commit()
        supplier_json = json.dumps(supplier.serialize())
        es_client.index(index=get_supplier_index_name(),
                        doc_type=SUPPLIER_DOC_TYPE,
                        body=supplier_json,
                        id=supplier.code)
    except TransportError, e:
        return jsonify(message=str(e)), e.status_code
    except IntegrityError as e:
        db.session.rollback()
        return jsonify(message="Database Error: {0}".format(e)), 400

    return jsonify(supplier=supplier.serialize()), success_code


@main.route('/suppliers', methods=['POST'])
def create_supplier():
    request_data = get_json_from_request()
    if 'supplier' in request_data:
        supplier_data = request_data.get('supplier')
    else:
        abort(400)

    supplier = Supplier()
    return update_supplier_data_impl(supplier, supplier_data, 201)


@main.route('/suppliers/<int:code>', methods=['POST', 'PATCH'])
def update_supplier(code):
    request_data = get_json_from_request()
    if 'supplier' in request_data:
        supplier_data = request_data.get('supplier')
    else:
        abort(400)

    if request.method == 'POST':
        supplier = Supplier(code=code)
    else:
        assert request.method == 'PATCH'
        supplier = Supplier.query.filter(
            Supplier.code == code
        ).first_or_404()

    return update_supplier_data_impl(supplier, supplier_data, 200)


@main.route('/suppliers/<int:code>/frameworks/<framework_slug>/declaration', methods=['PUT'])
def set_a_declaration(code, framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier_framework = SupplierFramework.find_by_supplier_and_framework(
        code, framework_slug
    )
    if supplier_framework is not None:
        status_code = 200 if supplier_framework.declaration else 201
    else:
        supplier = Supplier.query.filter(
            Supplier.code == code
        ).first_or_404()

        supplier_framework = SupplierFramework(
            supplier_code=supplier.code,
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


@main.route('/suppliers/<int:code>/frameworks/interest', methods=['GET'])
def get_registered_frameworks(code):
    supplier_frameworks = SupplierFramework.query.filter(
        SupplierFramework.supplier_code == code
    ).all()
    slugs = []
    for framework in supplier_frameworks:
        framework = Framework.query.filter(
            Framework.id == framework.framework_id
        ).first()
        slugs.append(framework.slug)

    return jsonify(frameworks=slugs)


@main.route('/suppliers/<int:code>/frameworks', methods=['GET'])
def get_supplier_frameworks_info(code):
    supplier = Supplier.query.filter(
        Supplier.code == code
    ).first_or_404()

    service_counts = SupplierFramework.get_service_counts(code)

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


@main.route('/suppliers/<int:code>/frameworks/<framework_slug>', methods=['GET'])
def get_supplier_framework_info(code, framework_slug):
    supplier_framework = SupplierFramework.find_by_supplier_and_framework(
        code, framework_slug
    )
    if supplier_framework is None:
        abort(404)

    return jsonify(frameworkInterest=supplier_framework.serialize())


@main.route('/suppliers/<int:code>/frameworks/<framework_slug>', methods=['PUT'])
def register_framework_interest(code, framework_slug):

    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier = Supplier.query.filter(
        Supplier.code == code
    ).first_or_404()

    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    json_payload.pop('updated_by')
    if json_payload:
        abort(400, "This PUT endpoint does not take a payload.")

    interest_record = SupplierFramework.query.filter(
        SupplierFramework.code == supplier.code,
        SupplierFramework.framework_id == framework.id
    ).first()
    if interest_record:
        return jsonify(frameworkInterest=interest_record.serialize()), 200

    if framework.status != 'open':
        abort(400, "'{}' framework is not open".format(framework_slug))

    interest_record = SupplierFramework(
        code=supplier.code,
        framework_id=framework.id,
        declaration={}
    )
    audit_event = AuditEvent(
        audit_type=AuditTypes.register_framework_interest,
        user=updater_json['updated_by'],
        data={'supplierId': supplier.code, 'frameworkSlug': framework_slug},
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


@main.route('/suppliers/<int:code>/frameworks/<framework_slug>', methods=['POST'])
def update_supplier_framework_details(code, framework_slug):

    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier = Supplier.query.filter(
        Supplier.code == code
    ).first_or_404()

    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    json_has_required_keys(json_payload, ["frameworkInterest"])
    update_json = json_payload["frameworkInterest"]

    interest_record = SupplierFramework.query.filter(
        SupplierFramework.code == supplier.code,
        SupplierFramework.framework_id == framework.id
    ).first()

    if not interest_record:
        abort(404, "code '{}' has not registered interest in {}".format(code, framework_slug))

    if 'onFramework' in update_json:
        interest_record.on_framework = update_json['onFramework']
    if 'agreementReturned' in update_json:
        if update_json['agreementReturned']:
            interest_record.agreement_returned_at = datetime.utcnow()
        else:
            interest_record.agreement_returned_at = None

    audit_event = AuditEvent(
        audit_type=AuditTypes.supplier_update,
        user=updater_json['updated_by'],
        data={'supplierId': supplier.code, 'frameworkSlug': framework_slug, 'update': update_json},
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
