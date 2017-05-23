from flask import jsonify, abort, request, current_app
from sqlalchemy.exc import IntegrityError, DataError

from dmapiclient.audit import AuditTypes

from .. import main
from ...models import db, Brief, BriefResponse, AuditEvent
from ...utils import (
    get_json_from_request, json_has_required_keys, get_int_or_400,
    pagination_links, get_valid_page_or_1, url_for,
    validate_and_return_updater_request,
)

from ...service_utils import validate_and_return_supplier


@main.route('/brief-responses', methods=['POST'])
def create_brief_response():
    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()

    json_has_required_keys(json_payload, ['briefResponses'])
    brief_response_json = json_payload['briefResponses']
    json_has_required_keys(brief_response_json, ['briefId', 'supplierCode'])

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

    # FIXME: The UK marketplace checks that the supplier has a relevant service and that its day rate meets the budget.
    # This Australian marketplace should do that too, but Australian suppliers haven't created services yet.

    # Check if brief response already exists from this supplier
    if BriefResponse.query.filter(BriefResponse.supplier == supplier, BriefResponse.brief == brief).first():
        abort(400, "Brief response already exists for supplier '{}'".format(supplier.code))

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


@main.route('/brief-responses/<int:brief_response_id>', methods=['GET'])
def get_brief_response(brief_response_id):
    brief_response = BriefResponse.query.filter(
        BriefResponse.id == brief_response_id
    ).first_or_404()

    return jsonify(briefResponses=brief_response.serialize())


@main.route('/brief-responses', methods=['GET'])
def list_brief_responses():
    page = get_valid_page_or_1()
    brief_id = get_int_or_400(request.args, 'brief_id')
    supplier_code = get_int_or_400(request.args, 'supplier_code')

    brief_responses = BriefResponse.query
    if supplier_code is not None:
        brief_responses = brief_responses.filter(BriefResponse.supplier_code == supplier_code)

    if brief_id is not None:
        brief_responses = brief_responses.filter(BriefResponse.brief_id == brief_id)

    if brief_id or supplier_code:
        return jsonify(
            briefResponses=[brief_response.serialize() for brief_response in brief_responses.all()],
            links={'self': url_for('.list_brief_responses', supplier_code=supplier_code, brief_id=brief_id)}
        )

    brief_responses = brief_responses.paginate(
        page=page,
        per_page=current_app.config['DM_API_BRIEF_RESPONSES_PAGE_SIZE']
    )

    return jsonify(
        briefResponses=[brief_response.serialize() for brief_response in brief_responses.items],
        links=pagination_links(
            brief_responses,
            '.list_brief_responses',
            request.args
        )
    )
