from flask import current_app, jsonify

from app.api import api
from app.api.helpers import role_required
from app.tasks.brief_response_tasks import update_brief_response_metrics
from app.tasks.brief_tasks import (create_responses_zip_for_closed_briefs,
                                   process_closed_briefs, update_brief_metrics)
from app.tasks.jira import (sync_application_approvals_with_jira,
                            sync_domain_assessment_approvals_with_jira)
from app.tasks.mailchimp import (send_new_briefs_email,
                                 sync_mailchimp_seller_list)
from app.tasks.supplier_tasks import update_supplier_metrics


@api.route('/tasks/process-closed-briefs', methods=['POST'])
@role_required('admin')
def run_process_closed_briefs():
    """Trigger Process Closed Brief
    ---
    tags:
      - tasks
    responses:
      200:
        type: string
        description: string
    """
    if current_app.config['CELERY_ASYNC_TASKING_ENABLED']:
        res = process_closed_briefs.delay()
        return jsonify(res.id)
    else:
        process_closed_briefs()
        return jsonify("finished")


@api.route('/tasks/maintain-seller-email-list', methods=['POST'])
@role_required('admin')
def run_maintain_seller_email_list():
    """Trigger Maintain Seller Email List
    ---
    tags:
      - tasks
    responses:
      200:
        type: string
        description: string
    """
    if current_app.config['CELERY_ASYNC_TASKING_ENABLED']:
        res = sync_mailchimp_seller_list.delay()
        return jsonify(res.id)
    else:
        sync_mailchimp_seller_list()
        return jsonify("finished")


@api.route('/tasks/send-daily-seller-email', methods=['POST'])
@role_required('admin')
def run_send_daily_seller_email():
    """Trigger Send Daily Seller Email
    ---
    tags:
      - tasks
    responses:
      200:
        type: string
        description: string
    """
    if current_app.config['CELERY_ASYNC_TASKING_ENABLED']:
        res = send_new_briefs_email.delay()
        return jsonify(res.id)
    else:
        send_new_briefs_email()
        return jsonify("finished")


@api.route('/tasks/create-responses-zip', methods=['POST'])
@role_required('admin')
def run_create_brief_responses_zip():
    """Trigger Create Brief Responses Zip
    ---
    tags:
      - tasks
    responses:
      200:
        type: string
        description: string
    """
    if current_app.config['CELERY_ASYNC_TASKING_ENABLED']:
        res = create_responses_zip_for_closed_briefs.delay()
        return jsonify(res.id)
    else:
        create_responses_zip_for_closed_briefs()
        return jsonify("finished")


@api.route('/tasks/update-brief-metrics', methods=['POST'])
@role_required('admin')
def run_update_brief_metrics():
    """Trigger Update Brief Metrics
    ---
    tags:
      - tasks
    responses:
      200:
        type: string
        description: string
    """
    if current_app.config['CELERY_ASYNC_TASKING_ENABLED']:
        res = update_brief_metrics.delay()
        return jsonify(res.id)
    else:
        update_brief_metrics()
        return jsonify("finished")


@api.route('/tasks/update-brief-response-metrics', methods=['POST'])
@role_required('admin')
def run_update_brief_response_metrics():
    """Trigger Update Brief Response Metrics
    ---
    tags:
      - tasks
    responses:
      200:
        type: string
        description: string
    """
    if current_app.config['CELERY_ASYNC_TASKING_ENABLED']:
        res = update_brief_response_metrics.delay()
        return jsonify(res.id)
    else:
        update_brief_response_metrics()
        return jsonify("finished")


@api.route('/tasks/update-supplier-metrics', methods=['POST'])
@role_required('admin')
def run_update_supplier_metrics():
    """Trigger Update Supplier Metrics
    ---
    tags:
      - tasks
    responses:
      200:
        type: string
        description: string
    """
    if current_app.config['CELERY_ASYNC_TASKING_ENABLED']:
        res = update_supplier_metrics.delay()
        return jsonify(res.id)
    else:
        update_supplier_metrics()
        return jsonify("finished")


@api.route('/tasks/update-all-metrics', methods=['POST'])
@role_required('admin')
def run_update_all_metrics():
    """Trigger Update All Metrics
    ---
    tags:
      - tasks
    responses:
      200:
        type: string
        description: string
    """
    if current_app.config['CELERY_ASYNC_TASKING_ENABLED']:
        return jsonify({
            "update_brief_metrics": update_brief_metrics.delay().id,
            "update_brief_response_metrics": update_brief_response_metrics.delay().id,
            "update_supplier_metrics": update_supplier_metrics.delay().id
        })
    else:
        update_brief_metrics()
        update_brief_response_metrics()
        update_supplier_metrics()
        return jsonify("finished")


@api.route('/tasks/sync-jira-application-approvals', methods=['POST'])
@role_required('admin')
def sync_jira_application_approvals():
    """Synchronise application approvals with Jira
    ---
    tags:
      - tasks
    responses:
      200:
        type: string
        description: string
    """
    if current_app.config['CELERY_ASYNC_TASKING_ENABLED']:
        res = sync_application_approvals_with_jira.delay()
        return jsonify(res.id)
    else:
        sync_application_approvals_with_jira()
        return jsonify("finished")


@api.route('/tasks/sync-jira-assessment-approvals', methods=['POST'])
@role_required('admin')
def sync_jira_assessment_approvals():
    """Synchronise domain assessment approvals with Jira
    ---
    tags:
      - tasks
    responses:
      200:
        type: string
        description: string
    """
    if current_app.config['CELERY_ASYNC_TASKING_ENABLED']:
        res = sync_domain_assessment_approvals_with_jira.delay()
        return jsonify(res.id)
    else:
        sync_domain_assessment_approvals_with_jira()
        return jsonify("finished")
