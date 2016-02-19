from flask import jsonify, abort, current_app, request

from dmapiclient.audit import AuditTypes
from .. import main
from ... import db
from ...models import User, Brief, AuditEvent
from ...utils import (
    get_json_from_request, get_int_or_400, json_has_required_keys, pagination_links,
    get_valid_page_or_1, get_request_page_questions, validate_and_return_updater_request
)
from ...service_utils import validate_and_return_lot
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

    if brief.status == 'live':
        abort(400, "Cannot update a live brief")

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
    briefs = Brief.query.order_by(Brief.id)
    page = get_valid_page_or_1()

    user_id = get_int_or_400(request.args, 'user_id')
    if user_id:
        briefs = briefs.filter(Brief.users.any(id=user_id))

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
