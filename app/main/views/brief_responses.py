from datetime import datetime
from dmutils.formats import DATE_FORMAT

from flask import abort, request, current_app
from sqlalchemy.exc import IntegrityError, DataError

from dmapiclient.audit import AuditTypes

from dmutils.config import convert_to_boolean

from .. import main
from ...models import db, Brief, BriefResponse, AuditEvent, Framework
from ...utils import (
    get_int_or_400,
    get_json_from_request,
    get_request_page_questions,
    get_valid_page_or_1,
    json_has_required_keys,
    list_result_response,
    paginated_result_response,
    single_result_response,
    validate_and_return_updater_request,
)

from ...brief_utils import get_supplier_service_eligible_for_brief
from ...service_utils import validate_and_return_supplier

COMPLETED_BRIEF_RESPONSE_STATUSES = ['submitted', 'pending-awarded', 'awarded']
RESOURCE_NAME = "briefResponses"


@main.route('/brief-responses', methods=['POST'])
def create_brief_response():
    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    page_questions = get_request_page_questions()

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

    if brief.framework.status not in ['live', 'expired']:
        abort(400, "Brief framework must be live or expired")

    supplier = validate_and_return_supplier(brief_response_json)

    brief_service = get_supplier_service_eligible_for_brief(supplier, brief)
    if not brief_service:
        abort(400, "Supplier is not eligible to apply to this brief")

    # Check if brief response already exists from this supplier
    if BriefResponse.query.filter(BriefResponse.supplier == supplier, BriefResponse.brief == brief).first():
        abort(400, "Brief response already exists for supplier '{}'".format(supplier.supplier_id))

    brief_response = BriefResponse(
        data=brief_response_json,
        supplier=supplier,
        brief=brief,
    )

    brief_role = brief.data["specialistRole"] if brief.lot.slug == "digital-specialists" else None
    service_max_day_rate = brief_service.data[brief_role + "PriceMax"] if brief_role else None

    brief_response.validate(enforce_required=False, required_fields=page_questions, max_day_rate=service_max_day_rate)

    db.session.add(brief_response)
    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    audit = AuditEvent(
        audit_type=AuditTypes.create_brief_response,
        user=updater_json['updated_by'],
        data={
            'briefResponseId': brief_response.id,
            'briefResponseJson': brief_response_json,
            'supplierId': supplier.supplier_id,
        },
        db_object=brief_response,
    )

    db.session.add(audit)
    db.session.commit()

    return single_result_response(RESOURCE_NAME, brief_response), 201


@main.route('/brief-responses/<int:brief_response_id>', methods=['POST'])
def update_brief_response(brief_response_id):
    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()
    page_questions = get_request_page_questions()

    json_has_required_keys(json_payload, ['briefResponses'])
    brief_response_json = json_payload['briefResponses']

    brief_response = BriefResponse.query.filter(
        BriefResponse.id == brief_response_id
    ).first_or_404()

    brief = brief_response.brief
    supplier = brief_response.supplier
    brief_service = get_supplier_service_eligible_for_brief(supplier, brief)
    if not brief_service:
        abort(400, "Supplier is not eligible to apply to this brief")

    if brief.status != 'live':
        abort(400, "Brief must have 'live' status for the brief response to be updated")

    if brief.framework.status not in ['live', 'expired']:
        abort(400, "Brief framework must be live or expired")

    brief_role = brief.data["specialistRole"] if brief.lot.slug == "digital-specialists" else None
    service_max_day_rate = brief_service.data[brief_role + "PriceMax"] if brief_role else None

    brief_response.update_from_json(brief_response_json)

    brief_response.validate(enforce_required=False, required_fields=page_questions, max_day_rate=service_max_day_rate)

    audit = AuditEvent(
        audit_type=AuditTypes.update_brief_response,
        user=updater_json['updated_by'],
        data={
            'briefResponseId': brief_response.id,
            'briefResponseData': brief_response_json,
            'supplierId': supplier.supplier_id,
        },
        db_object=brief_response,
    )

    db.session.add(brief_response)
    db.session.add(audit)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, brief_response), 200


@main.route('/brief-responses/<int:brief_response_id>/submit', methods=['POST'])
def submit_brief_response(brief_response_id):
    updater_json = validate_and_return_updater_request()

    brief_response = BriefResponse.query.filter(
        BriefResponse.id == brief_response_id
    ).first_or_404()

    brief = brief_response.brief
    supplier = brief_response.supplier
    brief_service = get_supplier_service_eligible_for_brief(supplier, brief)
    if not brief_service:
        abort(400, "Supplier is not eligible to apply to this brief")

    if brief.status != 'live':
        abort(400, "Brief must have 'live' status for the brief response to be submitted")

    if brief.framework.status not in ['live', 'expired']:
        abort(400, "Brief framework must be live or expired")

    brief_role = brief.data["specialistRole"] if brief.lot.slug == "digital-specialists" else None
    service_max_day_rate = brief_service.data[brief_role + "PriceMax"] if brief_role else None

    brief_response.validate(max_day_rate=service_max_day_rate)

    brief_response.submitted_at = datetime.utcnow()

    audit = AuditEvent(
        audit_type=AuditTypes.submit_brief_response,
        user=updater_json['updated_by'],
        data={
            'briefResponseId': brief_response.id,
            'supplierId': supplier.supplier_id,
        },
        db_object=brief_response,
    )

    db.session.add(brief_response)
    db.session.add(audit)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, brief_response), 200


@main.route('/brief-responses/<int:brief_response_id>', methods=['GET'])
def get_brief_response(brief_response_id):
    brief_response = BriefResponse.query.filter(
        BriefResponse.id == brief_response_id
    ).first_or_404()

    return single_result_response(RESOURCE_NAME, brief_response), 200


@main.route('/brief-responses', methods=['GET'])
def list_brief_responses():
    page = get_valid_page_or_1()
    brief_id = get_int_or_400(request.args, 'brief_id')
    supplier_id = get_int_or_400(request.args, 'supplier_id')
    awarded_at = request.args.get('awarded_at')
    with_data = convert_to_boolean(request.args.get("with-data", "true"))

    if request.args.get('status'):
        statuses = request.args['status'].split(',')
    else:
        statuses = COMPLETED_BRIEF_RESPONSE_STATUSES
    brief_responses = BriefResponse.query.filter(BriefResponse.status.in_(statuses))

    if supplier_id is not None:
        brief_responses = brief_responses.filter(BriefResponse.supplier_id == supplier_id)

    if brief_id is not None:
        brief_responses = brief_responses.filter(BriefResponse.brief_id == brief_id)

    if awarded_at is not None:
        day_start = datetime.strptime(awarded_at, DATE_FORMAT)
        day_end = datetime(day_start.year, day_start.month, day_start.day, 23, 59, 59, 999999)
        # Inclusive date range filtering
        brief_responses = brief_responses.filter(BriefResponse.awarded_at.between(day_start, day_end))

    brief_responses = brief_responses.options(
        db.defaultload(BriefResponse.brief).defaultload(Brief.framework).lazyload("*"),
        db.defaultload(BriefResponse.brief).defaultload(Brief.lot).lazyload("*"),
        db.defaultload(BriefResponse.brief).defaultload(Brief.awarded_brief_response).lazyload("*"),
        db.defaultload(BriefResponse.supplier).lazyload("*"),
    )

    if request.args.get('framework'):
        brief_responses = brief_responses.join(BriefResponse.brief).join(Brief.framework).filter(
            Brief.framework.has(Framework.slug.in_(
                framework_slug.strip() for framework_slug in request.args["framework"].split(",")
            ))
        )

    serialize_kwargs = {"with_data": with_data}

    if brief_id or supplier_id:
        return list_result_response(RESOURCE_NAME, brief_responses, serialize_kwargs=serialize_kwargs), 200

    return paginated_result_response(
        result_name=RESOURCE_NAME,
        results_query=brief_responses,
        serialize_kwargs=serialize_kwargs,
        page=page,
        per_page=current_app.config['DM_API_BRIEF_RESPONSES_PAGE_SIZE'],
        endpoint='.list_brief_responses',
        request_args=request.args
    ), 200
