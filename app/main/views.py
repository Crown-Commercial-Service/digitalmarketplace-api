from flask import render_template, jsonify, Response

from . import main
from ..lib.authentication import requires_authentication
from ..models import Service
from flask import abort
from flask import make_response
from flask import render_template
from flask import request

from app import services
from app.services import g6importService


@main.route('/')
@requires_authentication
def index():
    return render_template('main.html')


@main.route('/services/g6-scs-example')
@requires_authentication
def get_scs():
    content = render_template('sample_static_responses/sample-scs.json')
    resp = Response(response=content,
                    status=200,
                    mimetype="application/json")
    return resp


@main.route('/services/g6-saas-example')
@requires_authentication
def get_saas():
    content = render_template('sample_static_responses/sample-saas.json')
    resp = Response(response=content,
                    status=200,
                    mimetype="application/json")
    return resp


@main.route('/services/g6-paas-example')
@requires_authentication
def get_paas():
    content = render_template('sample_static_responses/sample-paas.json')
    resp = Response(response=content,
                    status=200,
                    mimetype="application/json")
    return resp


@main.route('/services/g6-iaas-example')
@requires_authentication
def get_iaas():
    content = render_template('sample_static_responses/sample-iaas.json')
    resp = Response(response=content,
                    status=200,
                    mimetype="application/json")
    return resp


@main.route('/services/<id>')
@requires_authentication
def get_service(id):
    service = Service.query.filter(Service.id == id).first_or_404()

    return jsonify(id=id, data=service.data)


# Test this locally by running the command:
# curl -i -H "Content-Type: application/json" \
# -H "Authorization: Bearer myToken" \
# -X POST \
# -d @example_listings/SSP-JSON-SCS.json \
# 127.0.0.1:5000/g6/service/add
@main.route('/g6/services', methods=['POST'])
@requires_authentication
def add_new_service():
    if not request.json:
        abort(400)
    validationResult = services.g6importService.validate_json(request.json)
    if validationResult:
        return 'JSON validated as %s' % validationResult
    else:
        return make_response("JSON was not a valid format", 422)
