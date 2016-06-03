from flask import jsonify, abort, current_app, request
from sqlalchemy.exc import IntegrityError

from dmapiclient.audit import AuditTypes
from .. import main
from ... import db
from ...models import User, Brief, AuditEvent, Framework, Lot, Supplier, Service
from ...utils import (
    get_json_from_request, get_int_or_400, json_has_required_keys, pagination_links,
    get_valid_page_or_1, get_request_page_questions, validate_and_return_updater_request
)
from ...service_utils import validate_and_return_lot, filter_services
from ...brief_utils import validate_brief_data


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
        abort(400, e.orig)

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

    return jsonify(briefs=brief.serialize()), 201


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

    return jsonify(briefs=brief.serialize()), 200


@main.route('/briefs/<int:brief_id>', methods=['GET'])
def get_brief(brief_id):
    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()

    return jsonify(briefs=brief.serialize(with_users=True))


@main.route('/briefs', methods=['GET'])
def list_briefs():
    briefs = Brief.query.order_by(Brief.published_at.desc(), Brief.id)
    page = get_valid_page_or_1()

    user_id = get_int_or_400(request.args, 'user_id')

    if user_id:
        briefs = briefs.filter(Brief.users.any(id=user_id))

    if request.args.get('framework'):
        briefs = briefs.filter(Brief.framework.has(Framework.slug == request.args.get('framework')))

    if request.args.get('lot'):
        briefs = briefs.filter(Brief.lot.has(Lot.slug == request.args.get('lot')))

    if request.args.get('status'):
        briefs = briefs.has_statuses(*[
            status.strip() for status in request.args['status'].split(',')
            ])

    if user_id:
        return jsonify(
            briefs=[brief.serialize() for brief in briefs.all()],
            links=dict()
        )
    else:
        briefs = briefs.paginate(
            page=page,
            per_page=current_app.config['DM_API_BRIEFS_PAGE_SIZE'])

        return jsonify(
            briefs=[brief.serialize() for brief in briefs.items],
            links=pagination_links(
                briefs,
                '.list_briefs',
                request.args
            )
        )


@main.route('/briefs/<int:brief_id>/status', methods=['PUT'])
def update_brief_status(brief_id):
    updater_json = validate_and_return_updater_request()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['briefs'])
    brief_json = json_payload['briefs']
    json_has_required_keys(brief_json, ['status'])

    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()

    if brief.framework.status != 'live':
        abort(400, "Framework is not live")

    if brief_json['status'] != brief.status:
        brief.status = brief_json['status']

        validate_brief_data(brief, enforce_required=True)

        audit = AuditEvent(
            audit_type=AuditTypes.update_brief_status,
            user=updater_json['updated_by'],
            data={
                'briefId': brief.id,
                'briefStatus': brief.status,
            },
            db_object=brief,
        )

        db.session.add(brief)
        db.session.add(audit)
        db.session.commit()

    return jsonify(briefs=brief.serialize()), 200


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
        abort(400, "Database Error: {0}".format(e))

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
        abort(400, e.orig)

    audit = AuditEvent(
        audit_type=AuditTypes.add_brief_clarification_question,
        user=updater_json["updated_by"],
        data=question_json,
        db_object=question,
    )

    db.session.add(audit)
    db.session.commit()

    return jsonify(briefs=brief.serialize()), 200


@main.route("/briefs/<brief_id>/services", methods=["GET"])
def list_brief_services(brief_id):
    brief = Brief.query.filter(
        Brief.id == brief_id
    ).filter(
        Brief.status == "live"
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

    return jsonify(services=[service.serialize() for service in services])
