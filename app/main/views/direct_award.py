from flask import jsonify, abort, current_app, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc, desc

from dmapiclient.audit import AuditTypes
from dmutils.config import convert_to_boolean
from .. import main
from ... import db
from ...models import User, AuditEvent
from ...models.direct_award import Project, Search
from ...utils import (
    get_json_from_request, get_int_or_400, json_has_required_keys, pagination_links,
    get_valid_page_or_1, validate_and_return_updater_request)


@main.route('/direct-award/projects', methods=['GET'])
def list_projects():
    page = get_valid_page_or_1()

    projects = Project.query
    user_id = get_int_or_400(request.args, 'user-id')
    if user_id:
        projects = projects.filter(Project.users.any(id=user_id))

    if 'latest-first' in request.args:
        if convert_to_boolean(request.args.get('latest-first')):
            projects = projects.order_by(desc(Project.created_at), desc(Project.id))
        else:
            projects = projects.order_by(asc(Project.created_at), asc(Project.id))
    else:
        projects = projects.order_by(asc(Project.id))

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
    json_has_required_keys(project_json, ['name', 'userId'])

    user = User.query.get(project_json.pop('userId'))
    if user is None:
        abort(400, "User ID not supplied")

    project = Project(name=project_json['name'], users=[user])
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
    project = Project.query.filter(Project.id == project_id).first_or_404()

    return jsonify(project=project.serialize())


@main.route('/direct-award/projects/<int:project_id>/searches', methods=['GET'])
def list_project_searches(project_id):
    page = get_valid_page_or_1()

    searches = Search.query.filter(Search.project_id == project_id)

    if 'latest-first' in request.args:
        if convert_to_boolean(request.args.get('latest-first')):
            searches = searches.order_by(desc(Search.created_at), desc(Search.id))
        else:
            searches = searches.order_by(asc(Search.created_at), asc(Search.id))
    else:
        searches = searches.order_by(asc(Search.id))

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
    json_has_required_keys(search_json, ['userId', 'searchUrl'])

    user = User.query.get(search_json.pop('userId'))
    if user is None:
        abort(400, "User ID not supplied")

    # TODO: Validate user has authorisation to access resource.

    db.session.query(Search).filter(Search.project_id == project_id).\
        update({Search.active: False})
    search = Search(created_by=user.id, project_id=project_id,
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
            'projectId': search.id,
            'searchJson': search_json,
        },
        db_object=search,
    )

    db.session.add(audit)
    db.session.commit()

    return jsonify(search=search.serialize()), 201


@main.route('/direct-award/projects/<int:project_id>/searches/<int:search_id>', methods=['GET'])
def get_project_search(project_id, search_id):
    search = Search.query.filter(
        Search.id == search_id,
        Search.project_id == project_id
    ).first_or_404()

    return jsonify(search=search.serialize())


@main.route('/direct-award/projects/<int:project_id>/services', methods=['GET'])
def list_project_services(project_id):
    raise NotImplementedError()
