from flask import jsonify, abort, current_app, request
from app.api.business import agency_business
from .. import main
from ...utils import get_json_from_request


@main.route('/admin/agency', methods=['GET'])
def get_agencies():
    agencies = agency_business.get_agencies()
    return jsonify(agencies=agencies)


@main.route('/admin/agency/<int:agency_id>', methods=['GET'])
def get_agency(agency_id):
    agency = agency_business.get_agency(agency_id)
    return jsonify(agency=agency)


@main.route('/admin/agency/<int:agency_id>', methods=['PUT'])
def update_agency(agency_id):
    json_payload = get_json_from_request()
    updated = json_payload.get('agency', None)
    update_details = json_payload.get('update_details')
    agency_business.update(agency_id, updated, update_details.get('updated_by'))
    agency = agency_business.get_agency(agency_id)
    return jsonify(agency=agency)
