from flask import jsonify, abort
from sqlalchemy.exc import IntegrityError, DataError

from dmapiclient.audit import AuditTypes

from .. import main
from ...models import db, Brief, BriefResponse, AuditEvent
from ...utils import (
    get_json_from_request, json_has_required_keys,
    validate_and_return_updater_request,
)

from ...service_utils import validate_and_return_supplier


@main.route('/brief-responses', methods=['POST'])
def create_brief_response():
    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()

    json_has_required_keys(json_payload, ['briefResponses'])
    brief_response_json = json_payload['briefResponses']
    json_has_required_keys(brief_response_json, ['briefId', 'supplierId'])

    try:
        brief = Brief.query.get(brief_response_json['briefId'])
    except DataError:
        brief = None

    if brief is None:
        abort(400, "Invalid brief ID '{}'".format(brief_response_json['briefId']))

    if brief.status != 'live':
        abort(400, "Brief must be live")

    if brief.framework.status != 'live':
        abort(400, "Brief framework must be live")

    supplier = validate_and_return_supplier(brief_response_json)

    brief_response = BriefResponse(
        data=brief_response_json,
        supplier=supplier,
        brief=brief,
    )

    brief_response.validate()

    db.session.add(brief_response)
    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig)

    audit = AuditEvent(
        audit_type=AuditTypes.create_brief_response,
        user=updater_json['updated_by'],
        data={
            'briefResponseId': brief_response.id,
            'briefResponseJson': brief_response_json,
        },
        db_object=brief_response,
    )

    db.session.add(audit)
    db.session.commit()

    return jsonify(briefResponses=brief_response.serialize()), 201


@main.route('/brief-responses/<int:brief_response_id>', methods=['POST'])
def get_brief_response(brief_response_id):
    pass
