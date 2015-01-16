from flask import (jsonify, Response, abort, render_template,
                   request, url_for)

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


@main.route('/services/g6-scs-example')
def get_scs():
    content = render_template('sample_static_responses/sample-scs.json')
    resp = Response(response=content,
                    status=200,
                    mimetype="application/json")
    return resp


@main.route('/services/g6-saas-example')
def get_saas():
    content = render_template('sample_static_responses/sample-saas.json')
    resp = Response(response=content,
                    status=200,
                    mimetype="application/json")
    return resp


@main.route('/services/g6-paas-example')
def get_paas():
    content = render_template('sample_static_responses/sample-paas.json')
    resp = Response(response=content,
                    status=200,
                    mimetype="application/json")
    return resp


@main.route('/services/g6-iaas-example')
def get_iaas():
    content = render_template('sample_static_responses/sample-iaas.json')
    resp = Response(response=content,
                    status=200,
                    mimetype="application/json")
    return resp


@main.route('/services', methods=['GET'])
def list_services():
    return jsonify(services=list(map(jsonify_service, Service.query.all())))


@main.route('/services', methods=['POST'])
def add_service():
    data = get_json_from_request()

    validate_json_or_400(data['services'])

    service = Service(data=data['services'])
    db.session.add(service)
    db.session.commit()

    return jsonify(services=jsonify_service(service)), 201


@main.route('/services/<service_id>', methods=['PUT'])
def update_service(service_id):
    service = Service.query.filter(Service.id == service_id).first_or_404()
    data = get_json_from_request()

    validate_json_or_400(data['services'])

    if data['services']['id'] != service.id:
        abort(400, "Invalid service ID provided")

    service.data = data['services']

    db.session.add(service)
    db.session.commit()

    return jsonify(services=jsonify_service(service)), 200


@main.route('/services/<service_id>', methods=['GET'])
def get_service(service_id):
    service = Service.query.filter(Service.id == service_id).first_or_404()

    return jsonify(services=jsonify_service(service))


def jsonify_service(service):
    data = dict(service.data.items())
    data['id'] = service.id

    data['links'] = [
        {
            "rel": "self",
            "href": url_for('.get_service',
                            service_id=service.id,
                            _external=True)
        }
    ]
    return data


def get_json_from_request():
    if request.content_type != 'application/json':
        abort(400, "Unexpected Content-Type, expecting 'application/json'")
    data = request.get_json()
    if data is None:
        abort(400, "Invalid JSON; must be a valid JSON object")
    if 'services' not in data:
        abort(400, "Invalid JSON must have a 'services' key")

    return data
