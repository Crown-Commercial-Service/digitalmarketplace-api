from datetime import datetime
import traceback

from flask import jsonify, abort, request
from sqlalchemy.exc import IntegrityError, DatabaseError

from .. import main
from ... import db
from ...models import ArchivedService, Service, Supplier, Framework
from ...validation import validate_json_or_400, \
    validate_updater_json_or_400, is_valid_service_id
from ..utils import url_for, pagination_links, drop_foreign_fields, \
    get_json_from_request, json_has_required_keys


# TODO: This should probably not be here
API_FETCH_PAGE_SIZE = 100


@main.route('/')
def index():
    """Entry point for the API, show the resources that are available."""
    return jsonify(links=[
        {
            "rel": "services.list",
            "href": url_for('.list_services', _external=True),
        },
        {
            "rel": "suppliers.list",
            "href": url_for('.list_suppliers', _external=True),
        },
    ]), 200


@main.route('/services', methods=['GET'])
def list_services():
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")

    supplier_id = request.args.get('supplier_id')

    services = Service.query
    if supplier_id is not None:
        try:
            supplier_id = int(supplier_id)
        except ValueError:
            abort(400, "Invalid supplier_id")

        supplier = Supplier.query.filter(Supplier.supplier_id == supplier_id) \
            .all()
        if not supplier:
            abort(404, "supplier_id '%d' not found" % supplier_id)

        services = services.filter(Service.supplier_id == supplier_id)

    services = services.paginate(page=page, per_page=API_FETCH_PAGE_SIZE,
                                 error_out=False)
    if page > 1 and not services.items:
        abort(404, "Page number out of range")
    return jsonify(
        services=[service.serialize() for service in services.items],
        links=pagination_links(
            services,
            '.list_services',
            request.args
        )
    )


@main.route('/archived-services', methods=['GET'])
def list_archived_services_by_service_id():
    """
    Retrieves a list of services from the archived_services table
    for the supplied service_id
    :query_param service_id:
    :return: List[service]
    """

    if not is_valid_service_id(
            request.args.get("service-id", "no service id")):
        abort(400, "Invalid service id supplied")
    else:
        service_id = request.args.get("service-id", "no service id")

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")

    services = ArchivedService.query.filter(Service.service_id == service_id)

    services = services.paginate(page=page, per_page=API_FETCH_PAGE_SIZE,
                                 error_out=False)

    if request.args and not services.items:
        abort(404)
    return jsonify(
        services=[service.serialize() for service in services.items],
        links=pagination_links(
            services,
            '.list_services',
            request.args
        )
    )


@main.route('/services/<string:service_id>', methods=['POST'])
def update_service(service_id):
    """
        Update a service. Looks service up in DB, and updates the JSON listing.
        Uses existing JSON Parse routines for validation
    """

    if not is_valid_service_id(service_id):
        abort(400, "Invalid service id supplied")

    service = Service.query.filter(
        Service.service_id == service_id
    ).first_or_404()

    service_to_archive = ArchivedService.from_service(service)

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["update_details", "services"])

    update_json = json_payload['update_details']
    validate_updater_json_or_400(update_json)
    service_update = drop_foreign_fields(
        json_payload['services'],
        ['supplierName', 'links']
    )

    data = dict(service.data.items())
    data.update(service_update)
    validate_json_or_400(data)

    now = datetime.now()
    service.data = data
    service.updated_at = now
    service.updated_by = update_json['updated_by']
    service.updated_reason = update_json['update_reason']

    db.session.add(service)
    db.session.add(service_to_archive)

    try:
        db.session.commit()
    except DatabaseError:
        traceback.print_exc()
        db.session.rollback()
        abort(500, "Database error")

    return jsonify(message="done"), 200


@main.route('/services/<string:service_id>', methods=['PUT'])
def import_service(service_id):

    if not is_valid_service_id(service_id):
        abort(400, "Invalid service id supplied")

    now = datetime.now()
    service = Service.query.filter(Service.service_id == service_id).first()

    http_status = 204
    if service is None:
        http_status = 201
        service = Service(service_id=service_id)
        service.created_at = now

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['services', 'update_details'])

    service_data = drop_foreign_fields(
        json_payload['services'],
        ['supplierName', 'links']
    )

    update_json = json_payload['update_details']
    validate_updater_json_or_400(update_json)

    validate_json_or_400(service_data)

    if str(service_data['id']) != str(service_id):
        abort(400, "Invalid service ID provided")

    service.data = service_data
    service.supplier_id = service_data['supplierId']
    service.framework_id = Framework.query.filter(
        Framework.name == "G-Cloud 6").first().id
    service.updated_at = now
    service.created_at = now
    service.status = "enabled"
    service.updated_by = update_json['updated_by']
    service.updated_reason = update_json['update_reason']

    db.session.add(service)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(400, "Unknown supplier ID provided")

    return "", http_status


@main.route('/services/<string:service_id>', methods=['GET'])
def get_service(service_id):

    if not is_valid_service_id(service_id):
        abort(400, "Invalid service id supplied")

    service = Service.query.filter(
        Service.service_id == service_id
    ).first_or_404()

    return jsonify(services=service.serialize())


@main.route('/archived-services/<int:archived_service_id>', methods=['GET'])
def get_archived_service(archived_service_id):
    """
    Retrieves a service from the archived_service by PK
    :param archived_service_id:
    :return: service
    """

    service = ArchivedService.query.filter(
        ArchivedService.id == archived_service_id
    ).first_or_404()

    return jsonify(services=service.serialize())
