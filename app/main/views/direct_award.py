from flask import jsonify, abort, current_app, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc

from dmapiclient.audit import AuditTypes
from .. import main
from ... import db
from ...models import User, DirectAwardProject, AuditEvent, DirectAwardSearch
from ...utils import (
    get_json_from_request, get_int_or_400, json_has_required_keys, pagination_links,
    get_valid_page_or_1, validate_and_return_updater_request, validate_user_can_access_direct_award_project_or_403)


@main.route('/direct-award/projects', methods=['GET'])
def list_projects():
    user_id = get_int_or_400(request.args, 'user_id')
    if user_id is None:
        abort(400, "User ID not supplied")

    page = get_valid_page_or_1()

    projects = DirectAwardProject.query.filter(DirectAwardProject.users.any(id=user_id))
    projects = projects.order_by(desc(DirectAwardProject.created_at), desc(DirectAwardProject.id))

    projects = projects.paginate(
        page=page,
        per_page=current_app.config['DM_API_PROJECTS_PAGE_SIZE'],
    )

    return jsonify(
        projects=[project.serialize() for project in projects.items],
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
    json_has_required_keys(project_json, ['name', 'user_id'])

    user = User.query.get(project_json.pop('user_id'))

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
            'project_id': project.id,
            'project_json': project_json,
        },
        db_object=project,
    )

    db.session.add(audit)
    db.session.commit()

    return jsonify(project=project.serialize()), 201


@main.route('/direct-award/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    user_id = get_int_or_400(request.args, 'user_id')
    if user_id is None:
        abort(400, "User ID not supplied")

    validate_user_can_access_direct_award_project_or_403(user_id, project_id)

    return jsonify(project=DirectAwardProject.query.get(project_id).serialize())


@main.route('/direct-award/projects/<int:project_id>/searches', methods=['GET'])
def list_project_searches(project_id):
    user_id = get_int_or_400(request.args, 'user_id')
    if user_id is None:
        abort(400, "User ID not supplied")

    validate_user_can_access_direct_award_project_or_403(user_id, project_id)

    page = get_valid_page_or_1()

    searches = DirectAwardSearch.query.filter(DirectAwardSearch.project_id == project_id)\
        .order_by(desc(DirectAwardSearch.created_at), desc(DirectAwardSearch.id))

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

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['search'])

    search_json = json_payload['search']
    json_has_required_keys(search_json, ['user_id', 'search_url'])

    user = User.query.get(search_json.pop('user_id'))

    if user is None:
        abort(400, "User ID not supplied")

    validate_user_can_access_direct_award_project_or_403(user.id, project_id)

    db.session.query(DirectAwardSearch).filter(DirectAwardSearch.project_id == project_id).\
        update({DirectAwardSearch.active: False})
    search = DirectAwardSearch(created_by=user.id, project_id=project_id,
                               search_url=search_json['search_url'], active=True)

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
            'project_id': search.id,
            'search_json': search_json,
        },
        db_object=search,
    )

    db.session.add(audit)
    db.session.commit()

    return jsonify(search=search.serialize()), 201


@main.route('/direct-award/projects/<int:project_id>/searches/<int:search_id>', methods=['GET'])
def get_project_search(project_id, search_id):
    user_id = get_int_or_400(request.args, 'user_id')
    if user_id is None:
        abort(400, "User ID not supplied")

    search = DirectAwardSearch.query.filter(
        DirectAwardSearch.id == search_id,
        DirectAwardSearch.project_id == project_id
    ).first_or_404()

    validate_user_can_access_direct_award_project_or_403(user_id, project_id)

    return jsonify(search=search.serialize())


@main.route('/direct-award/projects/<int:project_id>/services', methods=['GET'])
def list_project_services(project_id):
    raise NotImplementedError()
