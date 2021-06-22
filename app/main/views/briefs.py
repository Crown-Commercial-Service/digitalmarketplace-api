from dmutils.data_tools import ValidationError
from dmutils.filters import timesince
from flask import jsonify, abort, current_app, request
from sqlalchemy import desc
from sqlalchemy.orm import joinedload, lazyload, noload
from sqlalchemy.exc import IntegrityError
import pendulum
from pendulum.parsing.exceptions import ParserError

from app.api.services import (
    AuditTypes,
    briefs,
    suppliers,
    users,
    team_service
)
from app.tasks import publish_tasks
from .. import main
from ... import db
from ...models import (
    User,
    Brief,
    Domain,
    AuditEvent,
    Framework,
    Lot,
    Supplier,
    Service,
    TeamBrief
)
from ...utils import (
    get_json_from_request, get_int_or_400, json_has_required_keys, pagination_links,
    get_valid_page_or_1, get_request_page_questions, validate_and_return_updater_request,
    get_positive_int_or_400
)
from ...service_utils import validate_and_return_lot, filter_services
from ...brief_utils import (
    validate_brief_data,
    clean_brief_data,
    add_defaults
)
from ...datetime_utils import parse_time_of_day, combine_date_and_time
from app.emails.briefs import (
    send_brief_closed_email,
    send_specialist_brief_closed_email,
    send_seller_requested_feedback_from_buyer_email
)


@main.route('/briefs', methods=['POST'])
def create_brief():
    updater_json = validate_and_return_updater_request()
    page_questions = get_request_page_questions()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['briefs'])
    brief_json = json_payload['briefs']

    json_has_required_keys(brief_json, ['frameworkSlug', 'lot', 'userId'])

    add_defaults(brief_json)
    framework, lot = validate_and_return_lot(brief_json)

    if framework.status != 'live':
        abort(400, "Framework must be live")

    user = User.query.get(brief_json.pop('userId'))

    if user is None:
        abort(400, "User ID does not exist")

    teams = team_service.get_teams_for_user(user.id)
    team = None
    if len(teams) > 0:
        team = teams[0]
        team_brief = TeamBrief(
            team_id=team.id,
            user_id=user.id
        )
    if team:
        brief = Brief(data=brief_json, team_briefs=[team_brief], framework=framework, lot=lot)
    else:
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
        abort(400, "Cannot update a {} opportunity".format(brief.status))

    brief.update_from_json(brief_json)

    clean_brief_data(brief)
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


@main.route('/briefs/<int:brief_id>/users/<string:user>', methods=['PUT'])
def update_brief_add_user(brief_id, user):
    updater_json = validate_and_return_updater_request()
    brief = briefs.get(brief_id)

    if user.isdigit():
        u = [users.get(int(user))]
    else:
        u = [users.get_by_email(user)]
    if len(u) < 1:
        raise ValidationError("No user found: " + user)
    else:
        brief.users.append(u[0])
    audit = AuditEvent(
        audit_type=AuditTypes.update_brief,
        user=updater_json['updated_by'],
        data={
            'briefId': brief.id,
            'briefJson': {'add_user': user},
        },
        db_object=brief,
    )

    db.session.add(brief)
    db.session.add(audit)
    db.session.commit()

    return jsonify(briefs=brief.serialize(with_users=True)), 200


@main.route('/briefs/<int:brief_id>/suppliers/<int:supplier_code>', methods=['PUT'])
def update_brief_add_rfx_seller(brief_id, supplier_code):
    updater_json = validate_and_return_updater_request()
    # Using the helper.py methods to get the matching brief.
    brief = briefs.get(brief_id)
    supplier = suppliers.get_supplier_by_code(supplier_code)

    if not supplier:
        raise ValidationError("No supplier found: " + supplier_code)
    sellers = brief.data['sellers']
    sellers[str(supplier_code)] = {'name': supplier.name}
    brief.data['sellers'] = sellers
    audit = AuditEvent(
        audit_type=AuditTypes.seller_added_to_rfx_opportunity_admin,
        user=updater_json['updated_by'],
        data={
            'briefId': brief.id,
            'supplier_code': supplier_code,
        },
        db_object=brief,
    )

    db.session.add(brief)
    db.session.add(audit)
    db.session.commit()

    return jsonify(briefs=brief.serialize(with_users=True)), 200


@main.route('/briefs/<int:brief_id>/users/<string:user>', methods=['DELETE'])
def update_brief_remove_user(brief_id, user):
    updater_json = validate_and_return_updater_request()
    brief = briefs.get(brief_id)

    if user.isdigit():
        u = [users.get(int(user))]
    else:
        u = [users.get_by_email(user)]
    if len(u) < 1:
        raise ValidationError("No user found: " + user)
    else:
        brief.users.remove(u[0])
        audit = AuditEvent(
            audit_type=AuditTypes.update_brief,
            user=updater_json['updated_by'],
            data={
                'briefId': brief.id,
                'briefJson': {'remove_user': user},
            },
            db_object=brief,
        )

    db.session.add(brief)
    db.session.add(audit)
    db.session.commit()

    return jsonify(briefs=brief.serialize(with_users=True)), 200


@main.route('/briefs/<int:brief_id>/suppliers/<int:supplier_code>', methods=['DELETE'])
def update_brief_remove_rfx_seller(brief_id, supplier_code):
    updater_json = validate_and_return_updater_request()
    brief = briefs.get(brief_id)
    sellers = brief.data['sellers']

    for key in list(sellers.keys()):
        try:
            if key == str(supplier_code):
                del sellers[key]
        except KeyError:
            raise ValidationError("No supplier found: " + supplier_code)

    brief.data['sellers'] = sellers
    audit = AuditEvent(
        audit_type=AuditTypes.seller_removed_from_rfx_opportunity_admin,
        user=updater_json['updated_by'],
        data={
            'briefId': brief.id,
            'supplier_code': supplier_code,
        },
        db_object=brief,
    )

    db.session.add(brief)
    db.session.add(audit)
    db.session.commit()

    return jsonify(briefs=brief.serialize(with_users=True)), 200


@main.route('/briefs/<int:brief_id>/json/admin', methods=['PUT'])
def update_brief_json_admin(brief_id):
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['brief'])
    brief_json = json_payload['brief']

    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()

    if brief.status == 'live' or brief.status == 'draft':

        audit = AuditEvent(
            audit_type=AuditTypes.update_application_admin,
            user='',
            data={
                'new': brief_json,
                'old': brief.serialize()
            },
            db_object=brief,
        )
        brief.update_from_json(brief_json)

        db.session.add(brief)
        db.session.add(audit)
        db.session.commit()

        return jsonify(brief=brief.serialize()), 200
    else:
        return jsonify(
            brief=brief.serialize(),
            errors=[{
                'serverity': 'error',
                'message': 'Unable to update opportunities that are either closed or withdrawn'
            }]
        ), 200


@main.route('/briefs/<int:brief_id>/admin', methods=['POST'])
def update_brief_admin(brief_id):
    updater_json = validate_and_return_updater_request()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['briefs'])
    brief_json = json_payload['briefs']

    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()

    DEADLINES_TZ_NAME = current_app.config['DEADLINES_TZ_NAME']
    DEADLINES_TIME_OF_DAY = current_app.config['DEADLINES_TIME_OF_DAY']
    t = parse_time_of_day(DEADLINES_TIME_OF_DAY)
    if brief_json.get('clarification_questions_closed_at'):
        try:
            d = pendulum.parse(brief_json['clarification_questions_closed_at'])
            combined = combine_date_and_time(d, t, DEADLINES_TZ_NAME)
            brief.questions_closed_at = combined.in_timezone('UTC')
        except ParserError as e:
            raise ValidationError(str(e))

    applications_closed_at = brief_json.get('applications_closed_at')
    if applications_closed_at:
        try:
            d = pendulum.parse(brief_json['applications_closed_at'])
            combined = combine_date_and_time(d, t, DEADLINES_TZ_NAME)
            brief.closed_at = combined.in_timezone('UTC')
        except ParserError as e:
            raise ValidationError(str(e))

    if 'sellerEmailList' in brief_json:
        brief.update_from_json({'sellerEmailList': brief_json.get('sellerEmailList')})

    if 'sellerEmail' in brief_json:
        brief.update_from_json({'sellerEmail': brief_json.get('sellerEmail')})

    if 'areaOfExpertise' in brief_json:
        area_of_expertise = brief_json.get('areaOfExpertise', None)
        domain = Domain.get_by_name_or_id(area_of_expertise)
        seller_category = str(domain.id)

        brief.update_from_json({
            'areaOfExpertise': area_of_expertise,
            'sellerCategory': seller_category
        })

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

    if applications_closed_at:
        if (brief.closed_at <= pendulum.today()):
            send_brief_closed_email(brief)
            send_specialist_brief_closed_email(brief)

    return jsonify(briefs=brief.serialize(with_users=True)), 200


@main.route('/briefs/<int:brief_id>/send_feedback_email', methods=['POST'])
def send_feedback_email(brief_id):
    updater_json = validate_and_return_updater_request()
    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()

    send_seller_requested_feedback_from_buyer_email(brief)

    return jsonify(briefs=brief.serialize(with_users=True)), 200


@main.route('/briefs/<int:brief_id>/user/<int:user_id>', methods=['GET'])
def has_permission(brief_id, user_id):
    return jsonify(briefs.has_permission_to_brief(user_id, brief_id))


@main.route('/briefs/<int:brief_id>', methods=['GET'])
def get_brief(brief_id):
    brief = (
        Brief
        .query
        .filter(
            Brief.id == brief_id
        )
        .options(
            joinedload('users.frameworks'),
            joinedload('team_briefs'),
            joinedload('team_briefs.team.team_members'),
            noload('framework.lots')
        )
        .first_or_404()
    )
    return jsonify(briefs=brief.serialize(with_users=True))


@main.route('/briefs', methods=['GET'])
def list_briefs():
    if request.args.get('human'):
        briefs = Brief.query.options(joinedload(Brief.clarification_questions)) \
            .options(joinedload(Brief.users)).options(joinedload(Brief.work_order))\
            .order_by(Brief.status.desc(), Brief.published_at.desc())
    else:
        briefs = Brief.query.options(joinedload(Brief.clarification_questions)) \
            .options(joinedload(Brief.users)).options(joinedload(Brief.work_order))\
            .order_by(Brief.published_at.desc())

    page = get_valid_page_or_1()

    user_id = get_int_or_400(request.args, 'user_id')

    results_per_page = get_positive_int_or_400(
        request.args,
        'per_page',
        current_app.config['DM_API_SUPPLIERS_PAGE_SIZE']
    )

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

    if request.args.get('status'):
        stripped = (status.strip() for status in request.args['status'].split(','))
        briefs = briefs.has_statuses(*stripped)

    if user_id:
        return jsonify(
            briefs=[brief.serialize() for brief in briefs.all()],
            links={},
            meta={},
        )
    else:
        briefs = briefs.paginate(
            page=page,
            per_page=results_per_page,
        )

        return jsonify(
            briefs=[brief.serialize() for brief in briefs.items],
            meta={
                "total": briefs.total,
                "per_page": results_per_page
            },
            links=pagination_links(
                briefs,
                '.list_briefs',
                request.args
            ),
        )


@main.route('/briefs/count', methods=['GET'])
def get_briefs_stats():
    # workaround as 'Brief.withdrawn_at == None' gives pep8 error
    brief_query = Brief.query.options(lazyload('framework')).options(lazyload('lot'))\
        .filter(Brief.withdrawn_at.is_(None), Brief.published_at.isnot(None))
    all_briefs = brief_query.order_by(desc(Brief.published_at)).all()

    briefs = {
        'total': brief_query.count(),

        'live': brief_query.filter(Brief.closed_at.isnot(None), Brief.closed_at > pendulum.now()).count(),

        'open_to_all': brief_query.filter(Brief.data['sellerSelector'].astext == 'allSellers').count(),

        'open_to_selected': brief_query.filter(Brief.data['sellerSelector'].astext == 'someSellers').count(),

        'open_to_one': brief_query.filter(Brief.data['sellerSelector'].astext == 'oneSellers').count(),

        'recent_brief_time_since': (timesince(all_briefs[0].published_at)) if all_briefs else ''
    }

    return jsonify(briefs=briefs)


@main.route('/briefs/<int:brief_id>/status', methods=['PUT'])
def update_brief_status(brief_id):
    """Route is deprecated. Use `update_brief_status_by_action` instead."""
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


@main.route('/briefs/<int:brief_id>/<any(publish, withdraw):action>', methods=['POST'])
def update_brief_status_by_action(brief_id, action):
    updater_json = validate_and_return_updater_request()

    brief = Brief.query.filter(
        Brief.id == brief_id
    ).first_or_404()

    if brief.framework.status != 'live':
        abort(400, "Framework is not live")

    action_to_status = {
        'publish': 'live',
        'withdraw': 'withdrawn'
    }
    if brief.status != action_to_status[action]:
        previous_status = brief.status
        brief.status = action_to_status[action]

        if action == 'publish':
            validate_brief_data(brief, enforce_required=True)

        audit = AuditEvent(
            audit_type=AuditTypes.update_brief_status,
            user=updater_json['updated_by'],
            data={
                'briefId': brief.id,
                'briefPreviousStatus': previous_status,
                'briefStatus': brief.status,
            },
            db_object=brief,
        )

        db.session.add(brief)
        db.session.add(audit)
        db.session.commit()

        brief_url_external = '{}/2/digital-marketplace/opportunities/{}'.format(
            current_app.config['FRONTEND_ADDRESS'],
            brief_id
        )

        email_address = ''
        name = ''
        if len(brief.users) > 0:
            user = brief.users[0].serialize()
            email_address = user.get('email_address')
            name = user.get('name')

        publish_tasks.brief.delay(
            publish_tasks.compress_brief(brief),
            'published' if action == 'publish' else 'withdrawn',
            previous_status=previous_status,
            updated_by=updater_json['updated_by'],
            name=name,
            email_address=email_address,
            url=brief_url_external
        )

    return jsonify(briefs=brief.serialize()), 200


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
        abort(400, e.orig)

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

    return jsonify(briefs=new_brief.serialize()), 201


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
        abort(400, "Cannot delete a {} opportunity".format(brief.status))

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


@main.route("/briefs/<brief_id>/services", methods=["GET"])
def list_brief_services(brief_id):
    brief = Brief.query.filter(
        Brief.id == brief_id
    ).filter(
        Brief.status == "live"
    ).first_or_404()

    supplier_code = get_int_or_400(request.args, 'supplier_code')

    supplier = Supplier.query.filter(
        Supplier.code == supplier_code
    ).first_or_404()

    services = filter_services(
        framework_slugs=[brief.framework.slug],
        statuses=["published"],
        lot_slug=brief.lot.slug,
        role=brief.data["specialistRole"] if brief.lot.slug == "digital-specialists" else None
    )

    services = services.filter(Service.supplier_code == supplier.code)

    return jsonify(services=[service.serialize() for service in services])
