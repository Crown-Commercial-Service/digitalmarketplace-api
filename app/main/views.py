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

    service_to_archive = prepare_archived_service(service)
    validate_updater_json_or_400(get_json_from_request('updater')['updater'])
    service_update = get_json_from_request('serviceUpdate')['serviceUpdate']

    data = dict(service.data.items())
    data.update(service_update)
    validate_json_or_400(data)

    now = datetime.now()
    service.data = data
    service.updated_at = now
    service.updated_by = \
        get_json_from_request('updater')['updater']['username']
    service.updated_reason = \
        get_json_from_request('updater')['updater']['reason']

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
    http_status = 204
    if service is None:
        http_status = 201
        service = Service(service_id=service_id)
        service.created_at = now

    service_data = drop_foreign_fields(
        get_json_from_request('services')['services']
    )

    validate_json_or_400(service_data)

    if str(service_data['id']) != str(service_id):
        abort(400, "Invalid service ID provided")

    service.data = service_data
    service.supplier_id = service_data['supplierId']
    service.updated_at = now
    service.updated_by = 'importer'
    service.updated_reason = 'initial import'

    db.session.add(service)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(400, "Unknown supplier ID provided")

    return "", http_status


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

    try:
        int(service_archive_id)
    except ValueError:
        abort(400, "Invalid service id supplied")

    service = ServiceArchive.query.filter(
        ServiceArchive.id == service_archive_id
    ).first_or_404()

    return jsonify(services=jsonify_service(service))


def prepare_archived_service(service):
    """
    Makes a servicearchive instance based on this service
    :param Service:
    :return: ServiceArchive
    """
    return ServiceArchive(
        service_id=service.service_id,
        supplier_id=service.supplier_id,
        created_at=service.created_at,
        updated_at=service.updated_at,
        updated_by=service.updated_by,
        updated_reason=service.updated_reason,
        data=service.data
    )


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


def get_json_from_request(key):
    if request.content_type != 'application/json':
        abort(400, "Unexpected Content-Type, expecting 'application/json'")
    data = request.get_json()
    if data is None:
        abort(400, "Invalid JSON; must be a valid JSON object")
    if key not in data:
        abort(400, "Invalid JSON must have a '%s' key" % key)
    return data
