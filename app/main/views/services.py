from datetime import datetime

from flask import jsonify, abort, request, current_app

from .. import main
from ... import db
from ... import search_api_client
from ...models import ArchivedService, Service, Supplier, Framework
from sqlalchemy import asc
from sqlalchemy.exc import IntegrityError
from ...validation import detect_framework_or_400, \
    validate_updater_json_or_400, is_valid_service_id_or_400
from ...utils import url_for, pagination_links, drop_foreign_fields, link, \
    json_has_matching_id, get_json_from_request, json_has_required_keys
from sqlalchemy.types import String


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

    services = Service.query.order_by(
        asc(Service.framework_id),
        asc(Service.data['lot'].cast(String)),
        asc(Service.data['serviceName'].cast(String))
    )

    if request.args.get('status'):
        services = Service.query.filter(
            Service.status.in_(request.values.getlist('status'))
        )

    if supplier_id is not None:
        try:
            supplier_id = int(supplier_id)
        except ValueError:
            abort(400, "Invalid supplier_id: %s" % supplier_id)

    supplier = Supplier.query.filter(Supplier.supplier_id == supplier_id) \
        .all()
    if not supplier:
        abort(404, "supplier_id '%d' not found" % supplier_id)

    services = services.filter(Service.supplier_id == supplier_id)

    services = services.paginate(
        page=page,
        per_page=current_app.config['DM_API_SERVICES_PAGE_SIZE'],
        error_out=False,
    )

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

    is_valid_service_id_or_400(request.args.get("service-id", "no service id"))
    service_id = request.args.get("service-id", "no service id")

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")

    services = ArchivedService.query.filter(Service.service_id == service_id)

    services = services.paginate(
        page=page,
        per_page=current_app.config['DM_API_SERVICES_PAGE_SIZE'],
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

    is_valid_service_id_or_400(service_id)

    service = Service.query.filter(
        Service.service_id == service_id
    ).first_or_404()

    service_to_archive = ArchivedService.from_service(service)

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload,
                           ["update_details", "services"])

    update_json = json_payload['update_details']
    validate_updater_json_or_400(update_json)
    service_update = drop_foreign_fields(
        json_payload['services'],
        ['supplierName', 'links', 'frameworkName', 'status']
    )
    json_has_matching_id(service_update, service_id)

    data = dict(service.data.items())
    data.update(service_update)
    if "id" in data:
        # It is an old-style service JSON with an id field
        data["id"] = str(data["id"])
    else:
        # It is a new service JSON with id removed from payload already
        data["id"] = service_id
    detect_framework_or_400(data)

    data = drop_foreign_fields(data, ['id'])
    now = datetime.now()
    service.data = data
    service.updated_at = now
    service.updated_by = update_json['updated_by']
    service.updated_reason = update_json['update_reason']

    db.session.add(service)
    db.session.add(service_to_archive)

    try:
        db.session.commit()
        search_api_client.index(service_id, service.data,
                                service.supplier.name)
        return jsonify(message="done"), 200
    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig)


@main.route('/services/<string:service_id>', methods=['PUT'])
def import_service(service_id):
    is_valid_service_id_or_400(service_id)

    now = datetime.now()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload,
                           ['services', 'update_details'])

    service_data = drop_foreign_fields(
        json_payload['services'],
        ['supplierName', 'links']
    )
    json_has_matching_id(service_data, service_id)

    update_json = json_payload['update_details']
    validate_updater_json_or_400(update_json)

    framework = detect_framework_or_400(service_data)
    service_data = drop_foreign_fields(service_data, ['id'])

    service = Service.query.filter(Service.service_id == service_id).first()

    if service is None:
        service = Service(service_id=service_id)
        service.created_at = now
        supplier = Supplier.query.filter(
            Supplier.supplier_id == service_data['supplierId']).first()
        if supplier is None:
            abort(400,
                  "Key (supplierId)=({}) is not present"
                  .format(service_data['supplierId']))
    else:
        supplier = service.supplier

    service.supplier_id = service_data['supplierId']
    service.framework_id = Framework.query.filter(
        Framework.name == framework).first().id
    service.updated_at = now
    service.created_at = now
    if 'status' in service_data:
        service.status = service_data['status']
        service_data.pop('status', None)
    else:
        service.status = 'published'
    service.updated_by = update_json['updated_by']
    service.updated_reason = update_json['update_reason']
    service.data = service_data

    db.session.add(service)

    try:
        db.session.commit()
        search_api_client.index(service_id, service.data, supplier.name)
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return "", 201


@main.route('/services/<string:service_id>', methods=['GET'])
def get_service(service_id):
    is_valid_service_id_or_400(service_id)

    service = Service.query.filter(
        Service.service_id == service_id
    ).filter(Service.status == 'published').first_or_404()

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
