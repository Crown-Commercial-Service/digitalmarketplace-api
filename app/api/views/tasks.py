from flask import jsonify, current_app
from app.tasks.brief_tasks import process_closed_briefs
from app.tasks.mailchimp import sync_mailchimp_seller_list, send_new_briefs_email
from app.api import api
from app.api.helpers import role_required


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
