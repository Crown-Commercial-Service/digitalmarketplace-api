from flask import current_app

from app.api.services import (AuditTypes, application_service, assessments,
                              audit_service, domain_service,
                              suppliers)
from app.emails import (send_approval_notification,
                        send_assessment_approval_notification)
from app.jiraapi import get_marketplace_jira
from . import celery


@celery.task
def sync_application_approvals_with_jira():
    application_ids = application_service.get_submitted_application_ids()

    marketplace_jira = get_marketplace_jira()
    response = marketplace_jira.find_approved_application_issues(application_ids)

    application_id_field = current_app.config['JIRA_FIELD_CODES'].get('APPLICATION_FIELD_CODE')

    for issue in response['issues']:
        application_id = int(issue['fields'][application_id_field])
        application = application_service.get(application_id)
        if application and application.status == 'submitted':
            audit_service.log_audit_event(
                audit_type=AuditTypes.approve_application,
                user='Sync application approvals with Jira task',
                data={'jira_issue_key': issue['key']},
                db_object=application
            )

            application.set_approval(approved=True)
            application_service.commit_changes()
            send_approval_notification(application_id)


@celery.task
def sync_domain_assessment_approvals_with_jira():
    open_assessments = assessments.get_open_assessments()

    marketplace_jira = get_marketplace_jira()
    response = marketplace_jira.find_approved_assessment_issues(open_assessments)

    supplier_code_field = current_app.config['JIRA_FIELD_CODES'].get('SUPPLIER_FIELD_CODE')

    for issue in response['issues']:
        supplier = suppliers.get_supplier_by_code(issue['fields'][supplier_code_field])
        domain_name = issue['fields']['labels'][0].replace('_', ' ')
        if supplier and domain_name:
            supplier.update_domain_assessment_status(
                audit_data={'jira_issue_key': issue['key']},
                name_or_id=domain_name,
                status='assessed',
                user='Sync assessment approvals with Jira task'
            )
            application_service.commit_changes()
            domain = domain_service.get_by_name_or_id(domain_name)
            send_assessment_approval_notification(supplier.id, domain.id)
