from flask import jsonify, abort, request, current_app
from sqlalchemy.exc import IntegrityError

from app.main import main
from app.models import db, Project, AuditEvent
from app.utils import (
    get_json_from_request, json_has_required_keys, get_int_or_400,
    pagination_links, get_valid_page_or_1, url_for,
    get_positive_int_or_400, validate_and_return_updater_request
)

from app.service_utils import validate_and_return_supplier

from dmapiclient.audit import AuditTypes


def get_project_json():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['project'])
    return json_payload['project']


def save_project(project):
    db.session.add(project)
    db.session.commit()


@main.route('/projects', methods=['POST'])
def create_project():
    project_json = get_project_json()

    project = Project(
        data=project_json
    )
    save_project(project)

    return jsonify(project=project.serialize()), 201


@main.route('/projects/<int:project_id>', methods=['PATCH'])
def update_project(project_id):
    project_json = get_project_json()

    project = Project.query.get(project_id)
    if project is None:
        abort(404, "Project '{}' does not exist".format(project_id))

    project.update_from_json(project_json)
    save_project(project)

    return jsonify(project=project.serialize()), 200


@main.route('/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = Project.query.filter(
        Project.id == project_id
    ).first_or_404()

    return jsonify(project=project.serialize())


@main.route('/projects', methods=['GET'])
def list_projects():
    page = get_valid_page_or_1()

    projects = Project.query

    results_per_page = get_positive_int_or_400(
        request.args,
        'per_page',
        current_app.config['DM_API_PAGE_SIZE']
    )

    projects = projects.paginate(
        page=page,
        per_page=results_per_page
    )

    return jsonify(
        projects=[project.serialize() for project in projects.items],
        links=pagination_links(
            projects,
            '.list_projects',
            request.args
        )
    )
