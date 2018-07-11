import datetime

from flask import jsonify, abort, current_app, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc, desc
from app import search_api_client
from dmapiclient.audit import AuditTypes
from dmutils.config import convert_to_boolean

from .. import main
from ... import db
from ...models import User, AuditEvent, ArchivedService, Outcome
from ...models.direct_award import DirectAwardProject, DirectAwardSearch
from ...utils import (
    drop_all_other_fields,
    get_int_or_400,
    get_json_from_request,
    get_valid_page_or_1,
    json_has_required_keys,
    paginated_result_response,
    pagination_links,
    single_result_response,
    validate_and_return_updater_request,
)

from ...validation import validate_direct_award_project_json_or_400


def get_project_by_id_or_404(project_id: int):
    return DirectAwardProject.query.filter(DirectAwardProject.external_id == project_id).first_or_404()


@main.route('/direct-award/projects', methods=['GET'])
def list_projects():
    page = get_valid_page_or_1()

    projects = DirectAwardProject.query.options(
        db.joinedload(
            DirectAwardProject.outcome
        ).joinedload(
            Outcome.direct_award_archived_service
        ).load_only(
            "service_id"
        )
    )

    includes = request.args.get('include', '').split(',')

    with_users = 'users' in includes
    if with_users:
        projects = projects.options(db.joinedload('users').lazyload('supplier'))

    user_id = get_int_or_400(request.args, 'user-id')
    if user_id:
        projects = projects.filter(DirectAwardProject.users.any(id=user_id))

    if "having-outcome" in request.args:
        projects = projects.filter(
            db.cast(
                DirectAwardProject.outcome.has(),
                db.Boolean,
            ) == convert_to_boolean(request.args.get("having-outcome"))
        )

    if "locked" in request.args:
        projects = projects.filter(
            db.cast(
                DirectAwardProject.locked_at.isnot(None),
                db.Boolean,
            ) == convert_to_boolean(request.args.get("locked"))
        )

    if 'latest-first' in request.args:
        if convert_to_boolean(request.args.get('latest-first')):
            projects = projects.order_by(desc(DirectAwardProject.created_at), desc(DirectAwardProject.id))
        else:
            projects = projects.order_by(asc(DirectAwardProject.created_at), asc(DirectAwardProject.id))
    else:
        projects = projects.order_by(asc(DirectAwardProject.id))

    return paginated_result_response(
        result_name="projects",
        results_query=projects,
        page=page,
        per_page=current_app.config['DM_API_PROJECTS_PAGE_SIZE'],
        endpoint='.list_projects',
        request_args=request.args,
        serialize_kwargs={"with_users": with_users}
    ), 200


@main.route('/direct-award/projects', methods=['POST'])
def create_project():
    updater_json = validate_and_return_updater_request()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['project'])

    project_json = json_payload['project']
    json_has_required_keys(project_json, ['name', 'userId'])

    user = User.query.get(project_json.pop('userId'))
    if user is None:
        abort(400, "User ID not supplied")

    retries = 0
    while True:
        project = DirectAwardProject(name=project_json['name'], users=[user])
        db.session.add(project)

        try:
            db.session.flush()
            break

        except IntegrityError as e:
            current_app.logger.warning("Project ID collision on {}".format(project.external_id))
            db.session.rollback()

            retries += 1
            if retries >= 5:
                abort(400, format(e))

    audit = AuditEvent(
        audit_type=AuditTypes.create_project,
        user=updater_json['updated_by'],
        data={
            'projectExternalId': project.external_id,
            'projectJson': project_json,
        },
        db_object=project,
    )

    db.session.add(audit)
    db.session.commit()

    return single_result_response("project", project), 201


@main.route('/direct-award/projects/<int:project_external_id>', methods=['GET'])
def get_project(project_external_id):
    project = get_project_by_id_or_404(project_external_id)

    return single_result_response("project", project, serialize_kwargs={"with_users": True}), 200


@main.route('/direct-award/projects/<int:project_external_id>', methods=['PATCH'])
def update_project(project_external_id):
    uniform_now = datetime.datetime.utcnow()

    updater_json = validate_and_return_updater_request()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["project"])
    project_json = json_payload["project"]

    validate_direct_award_project_json_or_400(project_json)

    # fetch and lock row
    project = db.session.query(DirectAwardProject).filter_by(
        external_id=project_external_id,
    ).with_for_update().first()

    if not project:
        abort(404, f"Project {project_external_id} not found")

    # TODO: project.update_from_json(project_json)

    if project_json.get('stillAssessing'):
        if project.outcome:
            abort(400, "Cannot update stillAssessing when an outcome is present")
        project.still_assessing_at = uniform_now

    if project_json.get('readyToAssess') and project.ready_to_assess_at is None:
        if project.outcome:
            abort(400, "Cannot update readyToAssess when an outcome is present")
        project.ready_to_assess_at = uniform_now

    update_audit_event = AuditEvent(
        audit_type=AuditTypes.update_project,
        user=updater_json['updated_by'],
        db_object=project,
        data=project_json,
    )
    update_audit_event.created_at = uniform_now
    db.session.add(update_audit_event)

    db.session.commit()

    return single_result_response('project', project), 200


@main.route('/direct-award/projects/<int:project_external_id>/searches', methods=['GET'])
def list_project_searches(project_external_id):
    project = get_project_by_id_or_404(project_external_id)

    page = get_valid_page_or_1()

    searches = DirectAwardSearch.query.filter(DirectAwardSearch.project_id == project.id)

    if 'latest-first' in request.args:
        if convert_to_boolean(request.args.get('latest-first')):
            searches = searches.order_by(desc(DirectAwardSearch.created_at), desc(DirectAwardSearch.id))
        else:
            searches = searches.order_by(asc(DirectAwardSearch.created_at), asc(DirectAwardSearch.id))
    else:
        searches = searches.order_by(asc(DirectAwardSearch.id))

    if convert_to_boolean(request.args.get('only-active', False)):
        searches = searches.filter(DirectAwardSearch.active == True)  # noqa

    pagination_params = request.args.to_dict()
    pagination_params['project_external_id'] = project.external_id

    return paginated_result_response(
        result_name="searches",
        results_query=searches,
        page=page,
        per_page=current_app.config['DM_API_PROJECTS_PAGE_SIZE'],
        endpoint='.list_project_searches',
        request_args=pagination_params,
    ), 200


@main.route('/direct-award/projects/<int:project_external_id>/searches', methods=['POST'])
def create_project_search(project_external_id):
    updater_json = validate_and_return_updater_request()

    project = get_project_by_id_or_404(project_external_id)

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['search'])

    search_json = json_payload['search']
    json_has_required_keys(search_json, ['userId', 'searchUrl'])

    user = User.query.get(search_json.pop('userId'))
    if user is None:
        abort(400, "User ID not supplied")

    # TODO: Validate user has authorisation to access resource.

    db.session.query(DirectAwardSearch).filter(DirectAwardSearch.project_id == project.id).\
        update({DirectAwardSearch.active: False})
    search = DirectAwardSearch(created_by=user.id, project_id=project.id,
                               search_url=search_json['searchUrl'], active=True)

    db.session.add(search)

    try:
        db.session.flush()

    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    audit = AuditEvent(
        audit_type=AuditTypes.create_project_search,
        user=updater_json['updated_by'],
        data={
            'projectId': project.id,
            'projectExternalId': project.external_id,
            'searchJson': search_json,
        },
        db_object=search,
    )

    db.session.add(audit)
    db.session.commit()

    return single_result_response("search", search), 201


@main.route('/direct-award/projects/<int:project_external_id>/searches/<int:search_id>', methods=['GET'])
def get_project_search(project_external_id, search_id):
    project = get_project_by_id_or_404(project_external_id)

    search = DirectAwardSearch.query.filter(
        DirectAwardSearch.id == search_id,
        DirectAwardSearch.project_id == project.id
    ).first_or_404()

    return single_result_response("search", search), 200


@main.route('/direct-award/projects/<int:project_external_id>/services', methods=['GET'])
def list_project_services(project_external_id):
    """This endpoint returns all the services associated with a particular (locked) Direct Award Project. It returns
    some fairly arbitrary data which is obviously not ideal, but as we don't have a task runner that we can utilise to
    manage jobs like this and we need it to be responsive on-click, we're having to jerryrig in some data extraction and
    transformation in here. Specifically we are returning supplier name and contact information, and returning from
    the service data JSON keys as specified in the request (which will be loaded via a framework-specific manifest)."""
    page = get_valid_page_or_1()
    requested_fields = request.args.get('fields', '').split(',')
    project = get_project_by_id_or_404(project_external_id)

    if not project.locked_at:
        abort(400, 'Project has not been locked: {}'.format(project.external_id))

    # TODO: This should work for _all_ active searches, not just the first (although we currently enforce only one
    # TODO: active search) - SW 21/09/2017
    search = DirectAwardSearch.query.filter(
        DirectAwardSearch.project_id == project.id,
        DirectAwardSearch.active == True  # noqa
    ).first()
    if not search:
        abort(400, 'Project does not have a saved search: {}'.format(project.external_id))

    paginated_archived_services = search.archived_services.paginate(
        page=page,
        per_page=current_app.config['DM_API_PROJECTS_PAGE_SIZE'],
    )

    project_archived_services = list(map(lambda service: {
        'id': service.service_id,
        'projectId': project.external_id,
        'supplier': {
            'name': service.supplier.name,
            'contact': {
                'name': service.supplier.contact_information[0].contact_name,
                'phone': service.supplier.contact_information[0].phone_number,
                'email': service.supplier.contact_information[0].email,
            },
        },
        'data': drop_all_other_fields(service.data, requested_fields),
    }, paginated_archived_services.items))

    pagination_params = request.args.to_dict()
    pagination_params['project_external_id'] = project.external_id

    return jsonify(
        services=project_archived_services,
        meta={
            "total": paginated_archived_services.total,
        },
        links=pagination_links(
            paginated_archived_services,
            '.list_project_services',
            pagination_params
        ),
    ), 200


@main.route('/direct-award/projects/<int:project_external_id>/lock', methods=['POST'])
def lock_project(project_external_id):
    updater_json = validate_and_return_updater_request()

    project = get_project_by_id_or_404(project_external_id)

    if project.locked_at:
        abort(400, 'Project has already been locked: {}'.format(project.id))

    search = DirectAwardSearch.query.filter(
        DirectAwardSearch.project_id == project.id,
        DirectAwardSearch.active == True,  # noqa
    ).first_or_404()

    now = datetime.datetime.utcnow()

    service_ids = [service['id'] for service in search_api_client.search_services_from_url_iter(search.search_url,
                                                                                                id_only=True)]

    # We want the most recent ArchivedService for each service_id
    archived_services = ArchivedService.query.\
        filter(ArchivedService.service_id.in_(service_ids)).\
        group_by(ArchivedService.id).\
        order_by(ArchivedService.service_id, desc(ArchivedService.id)).\
        distinct(ArchivedService.service_id).all()

    search.searched_at = now
    search.archived_services = archived_services
    db.session.add(search)

    project.locked_at = now
    db.session.add(project)

    db.session.flush()

    audit = AuditEvent(
        audit_type=AuditTypes.lock_project,
        user=updater_json['updated_by'],
        data={
            'projectId': project.id,
            'projectExternalId': project.external_id,
        },
        db_object=search,
    )

    db.session.add(audit)
    db.session.commit()

    return single_result_response("project", project), 200


@main.route('/direct-award/projects/<int:project_external_id>/record-download', methods=['POST'])
def record_project_download(project_external_id):
    updater_json = validate_and_return_updater_request()

    project = get_project_by_id_or_404(project_external_id)

    # We want to track the latest datetime the results were downloaded, overriding previous (although they're audited).
    project.downloaded_at = datetime.datetime.utcnow()
    db.session.add(project)
    db.session.commit()

    audit = AuditEvent(
        audit_type=AuditTypes.downloaded_project,
        user=updater_json['updated_by'],
        data={
            'projectExternalId': project.external_id,
        },
        db_object=project,
    )

    db.session.add(audit)
    db.session.commit()

    return single_result_response("project", project), 200


@main.route('/direct-award/projects/<int:project_external_id>/services/<string:service_id>/award', methods=['POST'])
def create_award_outcome(project_external_id, service_id):
    updater_json = validate_and_return_updater_request()

    # Acquire share-lock on project and active search rows - what we're trying to assert here is that the "locked" field
    # of the project and the "active" field of the search are set to appropriate values at the time we create this
    # outcome
    project = db.session.query(DirectAwardProject).options(
        # this has to be performed as an inner join for the row-lock to work, just means we have to perform an extra
        # database hit in the no-rows case to disambiguate the error message
        db.joinedload(DirectAwardProject.active_search, innerjoin=True)
    ).filter(
        DirectAwardProject.external_id == project_external_id,
    ).with_for_update(read=True).first()

    if project is None:
        if db.session.query(DirectAwardProject.id).filter_by(external_id=project_external_id).first():
            # we reach the following conclusion by deduction...
            abort(404, f"Project {project_external_id} doesn't have an active search")
        else:
            abort(404, f"Project {project_external_id} not found")

    if not project.locked_at:
        abort(400, f"Project {project_external_id} has not been locked")

    if project.outcome is not None:
        abort(410, "Project {} already has a completed outcome: {}".format(
            project_external_id,
            project.outcome.external_id,
        ))

    archived_service = project.active_search.archived_services.options(db.load_only("id")).filter_by(
        service_id=service_id
    ).first()

    if not archived_service:
        abort(404, f"Service {service_id} is not in project {project_external_id}'s active search search results")

    # TODO? try-loop to assign ids, handling (unlikely) external_id collisions using sub-transaction so we don't lose
    # our DirectAwardProject row-lock
    outcome = Outcome(
        result="awarded",
        direct_award_project=project,
        direct_award_search=project.active_search,
        direct_award_archived_service=archived_service,
    )

    db.session.add(outcome)
    # ensure database constraints are happy with the object (initially at least: some constraints are only verified
    # on commit) and assign id
    db.session.flush()

    audit_event = AuditEvent(
        audit_type=AuditTypes.create_outcome,
        user=updater_json['updated_by'],
        data={
            "projectExternalId": project.external_id,
            "searchId": project.active_search.id,
            "archivedServiceId": archived_service.id,
            "result": outcome.result,
        },
        db_object=outcome,
    )
    db.session.add(audit_event)
    db.session.commit()

    return single_result_response("outcome", outcome), 200


@main.route(
    "/direct-award/projects/<int:project_external_id>/none-suitable",
    methods=("POST",),
    defaults={"nonawarded_reason": "none-suitable"},
)
@main.route(
    "/direct-award/projects/<int:project_external_id>/cancel",
    methods=("POST",),
    defaults={"nonawarded_reason": "cancelled"},
)
def create_nonawarded_outcome(project_external_id, nonawarded_reason):
    updater_json = validate_and_return_updater_request()
    uniform_now = datetime.datetime.utcnow()

    project = db.session.query(DirectAwardProject).filter_by(
        external_id=project_external_id,
    ).first()

    if project is None:
        abort(404, f"Project {project_external_id} not found")

    if project.outcome is not None:
        abort(410, "Project {} already has a completed outcome: {}".format(
            project_external_id,
            project.outcome.external_id,
        ))

    # TODO? try-loop to assign ids, handling (unlikely) external_id collisions using sub-transaction so we don't lose
    # any row-locks we might have
    outcome = Outcome(
        result=nonawarded_reason,
        direct_award_project=project,
    )
    outcome.completed_at = uniform_now

    db.session.add(outcome)
    # ensure database constraints are happy with the object (initially at least: some constraints are only verified
    # on commit) and assign id
    db.session.flush()

    creation_audit_event = AuditEvent(
        audit_type=AuditTypes.create_outcome,
        user=updater_json['updated_by'],
        data={
            "projectExternalId": project.external_id,
            "result": outcome.result,
        },
        db_object=outcome,
    )
    creation_audit_event.created_at = uniform_now
    db.session.add(creation_audit_event)

    completion_audit_event = AuditEvent(
        audit_type=AuditTypes.complete_outcome,
        user=updater_json['updated_by'],
        data={},
        db_object=outcome,
    )
    completion_audit_event.created_at = uniform_now
    db.session.add(completion_audit_event)
    db.session.commit()

    return single_result_response("outcome", outcome), 200
