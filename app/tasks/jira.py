from flask import current_app

from app.api.services import (AuditTypes, application_service, assessments,
                              audit_service, domain_service,
                              suppliers, evidence_service)
from app.emails import (send_approval_notification,
                        send_assessment_approval_notification)
from app.jiraapi import get_marketplace_jira
from . import celery


@celery.task
def create_evidence_assessment_in_jira(evidence_id):
    evidence = evidence_service.get_evidence_by_id(evidence_id)
    if not evidence:
        return False

    marketplace_jira = get_marketplace_jira()
    marketplace_jira.create_evidence_approval_task(evidence)
