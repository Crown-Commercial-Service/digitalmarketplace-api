from flask import current_app, jsonify, request

from app.api import api
from app.api.helpers import role_required
from app.tasks.brief_response_tasks import update_brief_response_metrics
from app.tasks.brief_tasks import (create_responses_zip_for_closed_briefs,
                                   process_closed_briefs, update_brief_metrics)
from app.tasks.jira import (sync_application_approvals_with_jira,
                            sync_domain_assessment_approvals_with_jira)
from app.tasks.mailchimp import (send_document_expiry_reminder,
                                 send_new_briefs_email,
                                 sync_mailchimp_seller_list)
from app.tasks.supplier_tasks import update_supplier_metrics
from app.tasks.dreamail import send_dreamail


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
    res = process_closed_briefs.delay()
    return jsonify(res.id)


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
    res = sync_mailchimp_seller_list.delay()
    return jsonify(res.id)


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
    res = send_new_briefs_email.delay()
    return jsonify(res.id)


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
    res = create_responses_zip_for_closed_briefs.delay()
    return jsonify(res.id)


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
    res = update_brief_metrics.delay()
    return jsonify(res.id)


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
    res = update_brief_response_metrics.delay()
    return jsonify(res.id)


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
    res = update_supplier_metrics.delay()
    return jsonify(res.id)


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
    return jsonify({
        "update_brief_metrics": update_brief_metrics.delay().id,
        "update_brief_response_metrics": update_brief_response_metrics.delay().id,
        "update_supplier_metrics": update_supplier_metrics.delay().id
    })


@api.route('/tasks/send-document-expiry-reminder', methods=['POST'])
@role_required('admin')
def send_document_expiry_reminder_email():
    """Send document expiry reminder
    ---
    tags:
      - tasks
    responses:
      200:
        type: string
        description: string
    """
    res = send_document_expiry_reminder.delay()
    return jsonify(res.id)


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
    res = sync_application_approvals_with_jira.delay()
    return jsonify(res.id)


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
    res = sync_domain_assessment_approvals_with_jira.delay()
    return jsonify(res.id)


@api.route('/tasks/send_dreamail', methods=['POST'])
@role_required('admin')
def run_send_dreamail():
    """Send email to suppliers notifying them of price and case study
       rejection
    ---
    tags:
      - tasks
    responses:
      200:
        type: string
        description: string
    """
    simulate = False if request.args.get('simulate') == 'False' else True
    skip_audit_check = True if request.args.get('skip_audit_check') == 'True' else False

    if simulate is False:
        res = send_dreamail.delay(simulate, skip_audit_check)
        return jsonify(res.id)
    else:
        return jsonify(send_dreamail(simulate, skip_audit_check)), 200
