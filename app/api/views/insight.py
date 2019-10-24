from flask import request, jsonify
from flask_login import current_user, login_required
import pendulum
from app.api import api
from app.api.helpers import (
    exception_logger,
    not_found,
    require_api_key_auth
)
from app.api.business import insight_business
from app.api.business.errors import NotFoundError
from app.utils import get_json_from_request


@api.route('/insight', methods=['GET'])
@exception_logger
def get_insight():
    now = None
    incoming_month_ending = request.args.get('monthEnding', None)
    if incoming_month_ending:
        now = pendulum.parse(incoming_month_ending)
    try:
        insight = insight_business.get_insight(current_user, now)
    except NotFoundError as nfe:
        not_found(nfe.message)

    return jsonify(insight), 200


@api.route('/insight', methods=['POST'])
@exception_logger
@require_api_key_auth
def upsert_insight():
    now = None
    incoming_month_ending = request.args.get('monthEnding', None)
    if incoming_month_ending:
        now = pendulum.parse(incoming_month_ending)

    json_payload = get_json_from_request()
    data = None
    if 'data' in json_payload:
        data = json_payload['data']

    active = None
    if 'active' in json_payload:
        active = json_payload['active']

    saved = insight_business.upsert(now, data, active)
    return jsonify(saved), 200
