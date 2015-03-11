from datetime import datetime
from flask import jsonify, abort, request
from flask import url_for as base_url_for
from sqlalchemy.exc import IntegrityError, DatabaseError

from . import main
from .. import db
from ..models import Service, ServiceArchive
from ..validation import validate_json_or_400, validate_updater_json_or_400


API_FETCH_PAGE_SIZE = 100


@main.route('/')
def index():
    """Entry point for the API, show the resources that are available."""
    return jsonify(links=[
        {
            "rel": "services.list",
            "href": url_for('.list_services', _external=True)
        }
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
        services = services.filter(Service.supplier_id == supplier_id)

    services = services.paginate(page=page, per_page=API_FETCH_PAGE_SIZE,
                                 error_out=False)
    if request.args and not services.items:
        abort(404)
    return jsonify(
        services=list(map(jsonify_service, services.items)),
        links=pagination_links(services, '.list_services', request.args))


@main.route('/services-archive', methods=['GET'])
def list_archived_services_by_service_id():
    """
    Retrieves a list of services from the service_archive table
    for the supplied service_id
    :query_param service_id:
    :return: List[service]
    """

    try:
        service_id = int(request.args.get("service-id", "no service id"))
    except ValueError:
        abort(400, "Invalid service id supplied")

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")

    services = ServiceArchive.query.filter(Service.service_id == service_id)

    services = services.paginate(page=page, per_page=API_FETCH_PAGE_SIZE,
                                 error_out=False)

    if request.args and not services.items:
        abort(404)
    return jsonify(
        services=list(map(jsonify_service, services.items)),
        links=pagination_links(services, '.list_services', request.args))


@main.route('/services/<int:service_id>', methods=['POST'])
def update_service(service_id):
    """
        Update a service. Looks service up in DB, and updates the JSON listing.
        Uses existing JSON Parse routines for validation
    """
    service = Service.query.filter(
        Service.service_id == service_id
    ).first_or_404()

    service_to_archive = ServiceArchive.from_service(service)

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["update_details", "services"])

    update_json = json_payload['update_details']
    validate_updater_json_or_400(update_json)
    service_update = json_payload['services']

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
        db.session.rollback()
        abort(500, "Database error")

    return jsonify(message="done"), 200


@main.route('/services/<int:service_id>', methods=['PUT'])
def import_service(service_id):
    now = datetime.now()
    service = Service.query.filter(Service.service_id == service_id).first()

    if service is not None:
        abort(409, "Service already exists")

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['services', 'update_details'])

    service_data = drop_foreign_fields(
        json_payload['services']
    )

    update_json = json_payload['update_details']
    validate_updater_json_or_400(update_json)

    validate_json_or_400(service_data)

    if str(service_data['id']) != str(service_id):
        abort(400, "Invalid service ID provided")

    service = Service(service_id=service_id)
    service.data = service_data
    service.supplier_id = service_data['supplierId']
    service.updated_at = now
    service.created_at = now
    service.updated_by = update_json['updated_by']
    service.updated_reason = update_json['update_reason']

    db.session.add(service)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(400, "Unknown supplier ID provided")

    return "", 201


@main.route('/services/<int:service_id>', methods=['GET'])
def get_service(service_id):
    service = Service.query.filter(
        Service.service_id == service_id
    ).first_or_404()

    return jsonify(services=jsonify_service(service))


@main.route('/services-archive/<int:service_archive_id>', methods=['GET'])
def get_archived_service(service_archive_id):
    """
    Retrieves a service from the service_archive by PK
    :param service_archive_id:
    :return: service
    """

    service = ServiceArchive.query.filter(
        ServiceArchive.id == service_archive_id
    ).first_or_404()

    return jsonify(services=jsonify_service(service))


def jsonify_service(service):
    data = dict(service.data.items())
    data.update({
        'id': service.service_id,
        'supplierId': service.supplier.supplier_id,
        'supplierName': service.supplier.name
    })

    data['links'] = [
        link("self", url_for(".get_service",
                             service_id=data['id']))
    ]
    return data


def drop_foreign_fields(service):
    service = service.copy()
    for key in ['supplierName', 'links']:
        service.pop(key, None)

    return service


def link(rel, href):
    if href is not None:
        return {
            "rel": rel,
            "href": href,
        }


def url_for(*args, **kwargs):
    kwargs.setdefault('_external', True)
    return base_url_for(*args, **kwargs)


def pagination_links(pagination, endpoint, args):
    return [
        link(rel, url_for(endpoint,
                          **dict(list(args.items()) +
                                 list({'page': page}.items()))))
        for rel, page in [('next', pagination.next_num),
                          ('prev', pagination.prev_num)]
        if 0 < page <= pagination.pages
    ]


def get_json_from_request():
    if request.content_type not in ['application/json',
                                    'application/json; charset=UTF-8']:
        abort(400, "Unexpected Content-Type, expecting 'application/json'")
    data = request.get_json()
    if data is None:
        abort(400, "Invalid JSON; must be a valid JSON object")
    return data


def json_has_required_keys(data, keys):
    for key in keys:
        if key not in data.keys():
            abort(400, "Invalid JSON must have '%s' key(s)" % keys)
