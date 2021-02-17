from datetime import datetime
from flask import jsonify, abort, current_app, request
from sqlalchemy.exc import IntegrityError

from dmapiclient.audit import AuditTypes
from .. import main
from ... import db
from ...models import User, Brief, BriefResponse, AuditEvent, Framework, Lot, Supplier, Service
from ...utils import (
    get_int_or_400,
    get_json_from_request,
    get_request_page_questions,
    get_valid_page_or_1,
    json_has_required_keys,
    list_result_response,
    single_result_response,
    paginated_result_response,
    purge_nulls_from_data,
    validate_and_return_updater_request,
)
from ...service_utils import validate_and_return_lot, filter_services
from ...brief_utils import index_brief, validate_brief_data
from ...validation import get_validation_errors

RESOURCE_NAME = "briefs"


@main.route('/briefs', methods=['POST'])
def create_brief():
    updater_json = validate_and_return_updater_request()
    page_questions = get_request_page_questions()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['briefs'])
    brief_json = json_payload['briefs']

    json_has_required_keys(brief_json, ['frameworkSlug', 'lot', 'userId'])

    framework, lot = validate_and_return_lot(brief_json)

    if framework.status != 'live':
        abort(400, "Framework must be live")

    user = User.query.get(brief_json.pop('userId'))

    if user is None:
        abort(400, "User ID does not exist")

    brief = Brief(data=brief_json, users=[user], framework=framework, lot=lot)
    validate_brief_data(brief, enforce_required=False, required_fields=page_questions)

    db.session.add(brief)
    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    audit = AuditEvent(
        audit_type=AuditTypes.create_brief,
        user=updater_json['updated_by'],
        data={
            'briefId': brief.id,
            'briefJson': brief_json,
        },
        db_object=brief,
    )

    db.session.add(audit)
    db.session.commit()
    # We are intentionally not indexing briefs here. We don't need drafts in search results, and they are indexed each
    # night by the batch indexing job run by Jenkins. In future we may index all briefs with a lower level ORM hook.

    return single_result_response(RESOURCE_NAME, brief), 201


@main.route('/briefs/<int:brief_id>', methods=['POST'])
def update_brief(brief_id):
    updater_json = validate_and_return_updater_request()
    page_questions = get_request_page_questions()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['briefs'])
    brief_json = json_payload['briefs']

    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()

    if brief.status != 'draft':
        abort(400, "Cannot update a {} brief".format(brief.status))

    brief.update_from_json(brief_json)

    validate_brief_data(brief, enforce_required=False, required_fields=page_questions)

    audit = AuditEvent(
        audit_type=AuditTypes.update_brief,
        user=updater_json['updated_by'],
        data={
            'briefId': brief.id,
            'briefJson': brief_json,
        },
        db_object=brief,
    )

    db.session.add(brief)
    db.session.add(audit)
    db.session.commit()
    # We are intentionally not indexing briefs here. We don't need drafts in search results, and they are indexed each
    # night by the batch indexing job run by Jenkins. In future we may index all briefs with a lower level ORM hook.

    return single_result_response(RESOURCE_NAME, brief), 200


@main.route('/briefs/<int:brief_id>', methods=['GET'])
def get_brief(brief_id):
    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()

    return single_result_response(
        RESOURCE_NAME,
        brief,
        serialize_kwargs={"with_users": True, "with_clarification_questions": True}
    ), 200


@main.route('/briefs', methods=['GET'])
def list_briefs():
    if request.args.get('human'):
        briefs = Brief.query.order_by(Brief.status_order, Brief.published_at.desc(), Brief.id)
    else:
        briefs = Brief.query.order_by(Brief.id)

    page = get_valid_page_or_1()

    with_users = request.args.get('with_users', 'false').lower() == 'true'

    with_clarification_questions = request.args.get('with_clarification_questions', 'false').lower() == 'true'

    user_id = get_int_or_400(request.args, 'user_id')

    if user_id:
        briefs = briefs.filter(Brief.users.any(id=user_id))

    if request.args.get('framework'):
        briefs = briefs.filter(Brief.framework.has(
            Framework.slug.in_(framework_slug.strip() for framework_slug in request.args["framework"].split(","))
        ))

    if request.args.get('lot'):
        briefs = briefs.filter(Brief.lot.has(
            Lot.slug.in_(lot_slug.strip() for lot_slug in request.args["lot"].split(","))
        ))

    response_headers = {"X-Compression-Safe": "0"}
    if request.args.get('status'):
        statuses = frozenset(status.strip() for status in request.args['status'].split(','))
        briefs = briefs.has_statuses(*statuses)

        if frozenset(("draft", "withdrawn",)).isdisjoint(statuses) and not with_users:
            # then all data we're returning is fairly public anyway
            response_headers["X-Compression-Safe"] = "1"

    status_filters = ['created', 'published', 'withdrawn', 'cancelled', 'unsuccessful', 'closed']
    temporal_filters = ['on', 'before', 'after']
    status_date_filters = [
        '{}_{}'.format(status, temporal) for status in status_filters for temporal in temporal_filters
    ]

    for status_date_key in [arg for arg in request.args.keys() if arg in status_date_filters]:
        status, temporal_filter = status_date_key.split('_')
        status = "applications_closed" if status == "closed" else status  # Hack for 'closed' status
        day_value = datetime.strptime(request.args.get(status_date_key), "%Y-%m-%d")
        if temporal_filter == 'on':
            day_end = datetime(day_value.year, day_value.month, day_value.day, 23, 59, 59, 999999)
            briefs = briefs.has_datetime_field_between("{}_at".format(status), day_value, day_end, inclusive=True)
        if temporal_filter == 'before':
            briefs = briefs.has_datetime_field_before("{}_at".format(status), day_value)
        if temporal_filter == 'after':
            day_end = datetime(day_value.year, day_value.month, day_value.day, 23, 59, 59, 999999)
            briefs = briefs.has_datetime_field_after("{}_at".format(status), day_end)

    if user_id:
        return list_result_response(
            RESOURCE_NAME,
            briefs,
            serialize_kwargs={"with_users": with_users, "with_clarification_questions": with_clarification_questions}
        ), 200, response_headers
    else:
        return paginated_result_response(
            result_name=RESOURCE_NAME,
            results_query=briefs,
            page=page,
            per_page=current_app.config['DM_API_BRIEFS_PAGE_SIZE'],
            endpoint='.list_briefs',
            request_args=request.args,
            serialize_kwargs={"with_users": with_users, "with_clarification_questions": with_clarification_questions}
        ), 200, response_headers


@main.route('/briefs/<int:brief_id>/<any(publish, withdraw, cancel, unsuccessful):action>', methods=['POST'])
def update_brief_status(brief_id, action):
    updater_json = validate_and_return_updater_request()

    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()
    framework_status = brief.framework.status

    action_to_status = {
        'publish': 'live',
        'withdraw': 'withdrawn',
        'cancel': 'cancelled',
        'unsuccessful': 'unsuccessful'
    }
    new_brief_status = action_to_status[action]

    if new_brief_status == 'live' and framework_status != 'live':
        abort(400, "Framework is not live")

    if brief.status != new_brief_status:
        old_brief_status = brief.status
        brief.status = new_brief_status

        if action == 'publish':
            validate_brief_data(brief, enforce_required=True)

        audit = AuditEvent(
            audit_type=AuditTypes.update_brief_status,
            user=updater_json['updated_by'],
            data={
                'briefId': brief.id,
                'briefPreviousStatus': old_brief_status,
                'briefStatus': brief.status,
            },
            db_object=brief,
        )

        db.session.add(brief)
        db.session.add(audit)
        db.session.commit()
        index_brief(brief)

    return single_result_response(RESOURCE_NAME, brief), 200


@main.route('/briefs/<int:brief_id>/award', methods=['POST'])
def award_pending_brief_response(brief_id):
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['briefResponseId'])
    updater_json = validate_and_return_updater_request()

    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()

    if not brief.status == 'closed':
        abort(400, "Brief is not closed")

    brief_responses = BriefResponse.query.filter(
        BriefResponse.brief_id == brief.id,
        BriefResponse.status != 'draft'
    )
    # Check that BriefResponse in POST data is associated with this brief
    if not json_payload['briefResponseId'] in [b.id for b in brief_responses]:
        abort(400, "BriefResponse cannot be awarded for this Brief")

    # Find any existing pending awarded BriefResponse and reset the details
    audit_events = []
    pending_awarded_responses = brief_responses.filter(BriefResponse.status == 'pending-awarded')
    for pending_awarded_response in pending_awarded_responses:
        pending_awarded_response.award_details = {}
        db.session.add(pending_awarded_response)
        audit_events.append(
            AuditEvent(
                audit_type=AuditTypes.update_brief_response,
                user=updater_json['updated_by'],
                data={
                    'briefId': brief.id,
                    'briefResponseId': pending_awarded_response.id,
                    'briefResponseAwardedValue': False
                },
                db_object=pending_awarded_response
            )
        )

    # Set new awarded BriefResponse
    brief_response = brief_responses.filter(BriefResponse.id == json_payload['briefResponseId']).first()
    brief_response.award_details = {'pending': True}
    audit_events.append(
        AuditEvent(
            audit_type=AuditTypes.update_brief_response,
            user=updater_json['updated_by'],
            data={
                'briefId': brief.id,
                'briefResponseId': brief_response.id,
                'briefResponseAwardedValue': True
            },
            db_object=brief_response
        )
    )

    db.session.add_all([brief_response] + audit_events)
    db.session.commit()

    return single_result_response(RESOURCE_NAME, brief), 200


@main.route('/briefs/<int:brief_id>/award/<int:brief_response_id>/contract-details', methods=['POST'])
def award_brief_details(brief_id, brief_response_id):
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['awardDetails'])
    updater_json = validate_and_return_updater_request()

    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()
    brief_response = BriefResponse.query.filter(
        BriefResponse.brief_id == brief_id,
        BriefResponse.id == brief_response_id
    ).first_or_404()

    if brief_response.status not in ('pending-awarded', 'awarded'):
        abort(400, "Cannot update award details for a Brief without a winning supplier")

    # Drop any null values to ensure correct validation messages
    award_details = purge_nulls_from_data(json_payload['awardDetails'])
    errors = get_validation_errors(
        'brief-awards-{}-{}'.format(brief.framework.slug, brief.lot.slug),
        award_details
    )
    if errors:
        abort(400, errors)

    brief_response.award_details = award_details
    if brief_response.status == 'pending-awarded':
        brief_response.awarded_at = datetime.utcnow()
    else:
        current_app.logger.info(
            "Updating previously awarded Brief so awarded_at is not reset. See audit event for details."
        )

    audit_event = AuditEvent(
        audit_type=AuditTypes.update_brief_response,
        user=updater_json['updated_by'],
        data={
            'briefId': brief.id,
            'briefResponseId': brief_response_id,
            'briefResponseAwardDetails': award_details
        },
        db_object=brief_response
    )

    db.session.add_all([brief_response, audit_event])
    db.session.commit()
    index_brief(brief)

    return single_result_response(RESOURCE_NAME, brief), 200


@main.route('/briefs/<int:brief_id>/award/<int:brief_response_id>/contract-details', methods=['DELETE'])
def un_award_brief_details(brief_id, brief_response_id):
    updater_json = validate_and_return_updater_request()

    brief_response = BriefResponse.query.filter(
        BriefResponse.brief_id == brief_id,
        BriefResponse.id == brief_response_id
    ).first_or_404()

    if brief_response.status != 'awarded':
        abort(400, "Can only un-award an awarded brief response")

    # Set status back to pending-awarded
    brief_response.awarded_at = None
    brief_response.award_details = {'pending': True}

    audit_event = AuditEvent(
        audit_type=AuditTypes.update_brief_response,
        user=updater_json['updated_by'],
        data={
            'briefId': brief_id,
            'briefResponseId': brief_response_id,
            'briefResponseAwardedValue': True,
            'unAwardBriefDetails': True
        },
        db_object=brief_response
    )

    db.session.add_all([brief_response, audit_event])
    db.session.commit()

    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()
    return single_result_response(RESOURCE_NAME, brief), 200


@main.route('/briefs/<int:brief_id>/copy', methods=['POST'])
def copy_brief(brief_id):
    updater_json = validate_and_return_updater_request()

    original_brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()

    new_brief = original_brief.copy()

    db.session.add(new_brief)
    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    audit = AuditEvent(
        audit_type=AuditTypes.create_brief,
        user=updater_json['updated_by'],
        data={
            'originalBriefId': original_brief.id,
            'briefId': new_brief.id
        },
        db_object=new_brief,
    )

    db.session.add(audit)
    db.session.commit()

    return single_result_response(RESOURCE_NAME, new_brief), 201


@main.route('/briefs/<int:brief_id>', methods=['DELETE'])
def delete_draft_brief(brief_id):
    """
    Delete a brief
    :param brief_id:
    :return:
    """

    updater_json = validate_and_return_updater_request()

    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()

    if brief.status != 'draft':
        abort(400, "Cannot delete a {} brief".format(brief.status))

    audit = AuditEvent(
        audit_type=AuditTypes.delete_brief,
        user=updater_json['updated_by'],
        data={
            "briefId": brief_id
        },
        db_object=None
    )

    db.session.delete(brief)
    db.session.add(audit)
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return jsonify(message="done"), 200


@main.route("/briefs/<int:brief_id>/clarification-questions", methods=["POST"])
def add_clarification_question(brief_id):
    updater_json = validate_and_return_updater_request()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['clarificationQuestion'])
    question_json = json_payload['clarificationQuestion']
    json_has_required_keys(question_json, ['question', 'answer'])

    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()

    question = brief.add_clarification_question(
        question_json.get('question'),
        question_json.get('answer'))

    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    audit = AuditEvent(
        audit_type=AuditTypes.add_brief_clarification_question,
        user=updater_json["updated_by"],
        data=question_json,
        db_object=question,
    )

    db.session.add(audit)
    db.session.commit()

    return single_result_response(
        RESOURCE_NAME,
        brief,
        serialize_kwargs={"with_clarification_questions": True}
    ), 200


@main.route("/briefs/<int:brief_id>/services", methods=["GET"])
def list_brief_services(brief_id):
    brief = Brief.query.filter(
        Brief.id == brief_id
    ).filter(
        Brief.status != "draft"
    ).first_or_404()

    supplier_id = get_int_or_400(request.args, 'supplier_id')

    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    services = filter_services(
        framework_slugs=[brief.framework.slug],
        statuses=["published"],
        lot_slug=brief.lot.slug,
        role=brief.data["specialistRole"] if brief.lot.slug == "digital-specialists" else None
    )

    services = services.filter(Service.supplier_id == supplier.supplier_id)
    return list_result_response("services", services), 200
