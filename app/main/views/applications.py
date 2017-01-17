from flask import jsonify, abort, request, current_app
from sqlalchemy.exc import IntegrityError, DataError

from app.jiraapi import get_marketplace_jira
from app.main import main
from app.models import db, Application, User
from app.utils import (
    get_json_from_request, json_has_required_keys, get_int_or_400,
    pagination_links, get_valid_page_or_1, url_for,
    get_positive_int_or_400, validate_and_return_updater_request
)


def get_application_json():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['application'])
    return json_payload['application']


def save_application(application):
    db.session.add(application)

    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig)

    db.session.commit()


@main.route('/applications', methods=['POST'])
def create_application():
    application_json = get_application_json()

    application = Application()
    application.update_from_json(application_json)

    save_application(application)

    return jsonify(application=application.serializable), 201


@main.route('/applications/<int:application_id>', methods=['PATCH'])
def update_application(application_id):
    application_json = get_application_json()

    application = Application.query.get(application_id)
    if application is None:
        abort(404, "Application '{}' does not exist".format(application_id))

    application.update_from_json(application_json)
    save_application(application)

    return jsonify(application=application.serializable), 200


@main.route('/applications/<int:application_id>/approve', methods=['POST'])
def approve_application(application_id):
    return application_approval(application_id, True)


@main.route('/applications/<int:application_id>/reject', methods=['POST'])
def reject_application(application_id):
    return application_approval(application_id, False)


def application_approval(application_id, result):
    application = Application.query.get(application_id)

    if application is None:
        abort(404, "Application '{}' does not exist".format(application_id))

    application.set_approval(approved=result)
    db.session.commit()
    return jsonify(application=application.serializable), 200


@main.route('/applications/<int:application_id>', methods=['GET'])
def get_application_by_id(application_id):
    application = Application.query.filter(
        Application.id == application_id
    ).first_or_404()
    return jsonify(application=application.serializable)


@main.route('/applications/<int:application_id>', methods=['DELETE'])
def delete_application(application_id):
    """
    Delete a Application
    :param application_id:
    :return:
    """

    application = Application.query.filter(
        Application.id == application_id
    ).first_or_404()

    db.session.delete(application)
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(message="done"), 200


def applications_list_response(with_task_status=False):
    page = get_valid_page_or_1()

    applications = Application.query

    ordering = request.args.get('order_by', 'application.created_at desc')
    order_by = ordering.split(',')

    applications = applications.order_by(*order_by)

    results_per_page = get_positive_int_or_400(
        request.args,
        'per_page',
        current_app.config['DM_API_PAGE_SIZE']
    )

    applications = applications.paginate(
        page=page,
        per_page=results_per_page
    )

    apps_results = [_.serializable for _ in applications.items]

    if with_task_status and current_app.config['JIRA_FEATURES']:
        def annotate_app(app):
            try:
                app['tasks'] = tasks_by_id[app['id']]
            except KeyError:
                pass
            return app

        jira = get_marketplace_jira()
        tasks_by_id = jira.assessment_tasks_by_application_id()
        apps_results = [annotate_app(_) for _ in apps_results]

    return jsonify(
        applications=apps_results,
        links=pagination_links(
            applications,
            '.list_applications',
            request.args
        )
    )


@main.route('/applications', methods=['GET'])
def list_applications():
    return applications_list_response(with_task_status=False)


@main.route('/applications/tasks', methods=['GET'])
def list_applications_taskstatus():
    return applications_list_response(with_task_status=True)
