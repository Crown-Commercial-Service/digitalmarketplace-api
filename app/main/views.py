from datetime import datetime
from flask import (jsonify, Response, abort, render_template,
                   request)
from flask import url_for as base_url_for

from . import main
from .. import db
from ..models import Service
from ..validation import validate_json_or_400


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
    if supplier_id is not None:
        try:
            supplier_id = int(supplier_id)
        except ValueError:
            abort(400, "Invalid supplier_id")
        services = Service.query.filter(Service.supplier_id == supplier_id)
    else:
        services = Service.query

    services = services.paginate(page=page, per_page=10, error_out=False)
    if request.args and not services.items:
        abort(404)
    return jsonify(
        services=list(map(jsonify_service, services.items)),
        links=pagination_links(services, '.list_services', request.args))


@main.route('/services', methods=['POST'])
def add_service():
    message = "IDs are currently generated externally, new resources should " \
              "be created with PUT"
    return jsonify(error=message), 501


@main.route('/services/<int:service_id>', methods=['PUT'])
def update_service(service_id):
    now = datetime.now()
    service = Service.query.filter(Service.service_id == service_id).first()
    http_status = 204
    if service is None:
        http_status = 201
        service = Service(service_id=service_id)
        service.created_at = now
    data = get_json_from_request()

    validate_json_or_400(data['services'])

    if str(data['services']['id']) != str(service_id):
        abort(400, "Invalid service ID provided")

    service.data = data['services']
    service.supplier_id = data['services']['supplierId']
    service.updated_at = now
    db.session.add(service)
    db.session.commit()

    return "", http_status


@main.route('/services/<int:service_id>', methods=['GET'])
def get_service(service_id):
    service = Service.query.filter(Service.service_id == service_id)\
                           .first_or_404()

    return jsonify(services=jsonify_service(service))


def jsonify_service(service):
    data = dict(service.data.items())
    data.update({
        'id': service.service_id,
        'supplierId': service.supplier_id,
    })

    data['links'] = [
        link("self", url_for(".get_service",
                             service_id=data['id']))
    ]
    return data


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
    if request.content_type != 'application/json':
        abort(400, "Unexpected Content-Type, expecting 'application/json'")
    data = request.get_json()
    if data is None:
        abort(400, "Invalid JSON; must be a valid JSON object")
    if 'services' not in data:
        abort(400, "Invalid JSON must have a 'services' key")

    return data
