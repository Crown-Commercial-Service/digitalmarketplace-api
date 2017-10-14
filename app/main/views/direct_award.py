import datetime
from flask import jsonify, abort, current_app, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc, desc

from app import search_api_client
from dmapiclient.audit import AuditTypes
from dmutils.config import convert_to_boolean
from .. import main
from ... import db
from ...models import User, AuditEvent, ArchivedService
from ...models.direct_award import DirectAwardProject, DirectAwardSearch
from ...utils import (
    get_json_from_request, get_int_or_400, json_has_required_keys, pagination_links,
    get_valid_page_or_1, validate_and_return_updater_request, drop_all_other_fields)


@main.route('/direct-award/projects', methods=['GET'])
def list_projects():
    page = get_valid_page_or_1()

    projects = DirectAwardProject.query

    with_users = convert_to_boolean(request.args.get('with-users', False))
    if not isinstance(with_users, bool):
        abort(400, "with-users param must be True of False")

    user_id = get_int_or_400(request.args, 'user-id')
    if user_id:
        projects = projects.filter(DirectAwardProject.users.any(id=user_id))

    if 'latest-first' in request.args:
        if convert_to_boolean(request.args.get('latest-first')):
            projects = projects.order_by(desc(DirectAwardProject.created_at), desc(DirectAwardProject.id))
        else:
            projects = projects.order_by(asc(DirectAwardProject.created_at), asc(DirectAwardProject.id))
    else:
        projects = projects.order_by(asc(DirectAwardProject.id))

    projects = projects.paginate(
        page=page,
        per_page=current_app.config['DM_API_PROJECTS_PAGE_SIZE'],
    )

    return jsonify(
        projects=[project.serialize(with_users=with_users) for project in projects.items],
        meta={
            "total": projects.total,
        },
        links=pagination_links(
            projects,
            '.list_projects',
            request.args
        ),
    )


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

    project = DirectAwardProject(name=project_json['name'], users=[user])
    db.session.add(project)

    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig)

    audit = AuditEvent(
        audit_type=AuditTypes.create_project,
        user=updater_json['updated_by'],
        data={
            'projectId': project.id,
            'projectJson': project_json,
        },
        db_object=project,
    )

    db.session.add(audit)
    db.session.commit()

    return jsonify(project=project.serialize()), 201


@main.route('/direct-award/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = DirectAwardProject.query.filter(DirectAwardProject.id == project_id).first_or_404()

    return jsonify(project=project.serialize(with_users=True))


@main.route('/direct-award/projects/<int:project_id>/searches', methods=['GET'])
def list_project_searches(project_id):
    # If the project doesn't exist, we should 404 early.
    DirectAwardProject.query.filter(DirectAwardProject.id == project_id).first_or_404()

    page = get_valid_page_or_1()

    searches = DirectAwardSearch.query.filter(DirectAwardSearch.project_id == project_id)

    if 'latest-first' in request.args:
        if convert_to_boolean(request.args.get('latest-first')):
            searches = searches.order_by(desc(DirectAwardSearch.created_at), desc(DirectAwardSearch.id))
        else:
            searches = searches.order_by(asc(DirectAwardSearch.created_at), asc(DirectAwardSearch.id))
    else:
        searches = searches.order_by(asc(DirectAwardSearch.id))

    if convert_to_boolean(request.args.get('only-active', False)):
        searches = searches.filter(DirectAwardSearch.active == True)  # noqa

    searches = searches.paginate(
        page=page,
        per_page=current_app.config['DM_API_PROJECTS_PAGE_SIZE'],
    )

    pagination_params = request.args.to_dict()
    pagination_params['project_id'] = project_id

    return jsonify(
        searches=[search.serialize() for search in searches.items],
        meta={
            "total": searches.total,
        },
        links=pagination_links(
            searches,
            '.list_project_searches',
            pagination_params
        ),
    )


@main.route('/direct-award/projects/<int:project_id>/searches', methods=['POST'])
def create_project_search(project_id):
    updater_json = validate_and_return_updater_request()

    # If the project doesn't exist, we should 404 early.
    DirectAwardProject.query.filter(DirectAwardProject.id == project_id).first_or_404()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['search'])

    search_json = json_payload['search']
    json_has_required_keys(search_json, ['userId', 'searchUrl'])

    user = User.query.get(search_json.pop('userId'))
    if user is None:
        abort(400, "User ID not supplied")

    # TODO: Validate user has authorisation to access resource.

    db.session.query(DirectAwardSearch).filter(DirectAwardSearch.project_id == project_id).\
        update({DirectAwardSearch.active: False})
    search = DirectAwardSearch(created_by=user.id, project_id=project_id,
                               search_url=search_json['searchUrl'], active=True)

    db.session.add(search)

    try:
        db.session.flush()

    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig)

    audit = AuditEvent(
        audit_type=AuditTypes.create_project_search,
        user=updater_json['updated_by'],
        data={
            'projectId': project_id,
            'searchJson': search_json,
        },
        db_object=search,
    )

    db.session.add(audit)
    db.session.commit()

    return jsonify(search=search.serialize()), 201


@main.route('/direct-award/projects/<int:project_id>/searches/<int:search_id>', methods=['GET'])
def get_project_search(project_id, search_id):
    # If the project doesn't exist, we should 404 early.
    DirectAwardProject.query.filter(DirectAwardProject.id == project_id).first_or_404()

    search = DirectAwardSearch.query.filter(
        DirectAwardSearch.id == search_id,
        DirectAwardSearch.project_id == project_id
    ).first_or_404()

    return jsonify(search=search.serialize())


@main.route('/direct-award/projects/<int:project_id>/services', methods=['GET'])
def list_project_services(project_id):
    """This endpoint returns all the services associated with a particular (locked) Direct Award Project. It returns
    some fairly arbitrary data which is obviously not ideal, but as we don't have a task runner that we can utilise to
    manage jobs like this and we need it to be responsive on-click, we're having to jerryrig in some data extraction and
    transformation in here. Specifically we are returning supplier name and contact information, and returning from
    the service data JSON keys as specified in the request (which will be loaded via a framework-specific manifest)."""
    page = get_valid_page_or_1()
    requested_fields = request.args.get('fields', '').split(',')
    project = DirectAwardProject.query.filter(DirectAwardProject.id == project_id).first_or_404()

    if not project.locked_at:
        abort(400, 'Project has not been locked: {}'.format(project_id))

    # TODO: This should work for _all_ active searches, not just the first (although we currently enforce only one
    # TODO: active search) - SW 21/09/2017
    search = DirectAwardSearch.query.filter(
        DirectAwardSearch.project_id == project_id,
        DirectAwardSearch.active == True  # noqa
    ).first()
    if not search:
        abort(400, 'Project does not have a saved search: {}'.format(project_id))

    paginated_archived_services = search.archived_services.paginate(
        page=page,
        per_page=current_app.config['DM_API_PROJECTS_PAGE_SIZE'],
    )

    project_archived_services = list(map(lambda service: {
        'id': service.service_id,
        'projectId': project_id,
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
    pagination_params['project_id'] = project_id

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
    )


@main.route('/direct-award/projects/<int:project_id>/lock', methods=['POST'])
def lock_project(project_id):
    updater_json = validate_and_return_updater_request()

    project = DirectAwardProject.query.filter(DirectAwardProject.id == project_id).first_or_404()

    if project.locked_at:
        abort(400, 'Project has already been locked: {}'.format(project_id))

    search = DirectAwardSearch.query.filter(
        DirectAwardSearch.project_id == project_id,
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

    db.session.commit()

    audit = AuditEvent(
        audit_type=AuditTypes.lock_project,
        user=updater_json['updated_by'],
        data={
            'projectId': project.id
        },
        db_object=search,
    )

    db.session.add(audit)
    db.session.commit()

    return jsonify(project=project.serialize())


@main.route('/direct-award/projects/<int:project_id>/record-download', methods=['POST'])
def record_project_download(project_id):
    updater_json = validate_and_return_updater_request()

    project = DirectAwardProject.query.filter(DirectAwardProject.id == project_id).first_or_404()

    # We want to track the latest datetime the results were downloaded, overriding previous (although they're audited).
    project.downloaded_at = datetime.datetime.utcnow()
    db.session.add(project)
    db.session.commit()

    audit = AuditEvent(
        audit_type=AuditTypes.downloaded_project,
        user=updater_json['updated_by'],
        data={
            'projectId': project.id
        },
        db_object=project,
    )

    db.session.add(audit)
    db.session.commit()

    return jsonify(project=project.serialize())
