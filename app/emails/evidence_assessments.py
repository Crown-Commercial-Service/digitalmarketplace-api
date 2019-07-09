from flask import current_app
from app.api.services import domain_service, suppliers, users
from .util import render_email_template, send_or_handle_error


def send_evidence_assessment_requested_notification(domain_id, user_email):
    template_filename = 'evidence_assessment_requested.md'

    frontend_address = current_app.config['FRONTEND_ADDRESS']

    domain = domain_service.find(id=domain_id).one_or_none()

    if not domain:
        raise Exception('invalid domain id')

    email_addresses = [user_email]

    # prepare copy
    email_body = render_email_template(
        template_filename,
        frontend_address=frontend_address,
        domain_name=domain.name,
        current_user_email=user_email
    )

    subject = "Assessment request for %s received" % (domain.name)

    send_or_handle_error(
        email_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='evidence assessment approved'
    )


def send_evidence_assessment_approval_notification(evidence):
    template_filename = 'evidence_assessment_approved.md'

    frontend_address = current_app.config['FRONTEND_ADDRESS']

    domain = domain_service.find(id=evidence.domain_id).one_or_none()
    user = users.find(id=evidence.user_id).one_or_none()

    if not domain or not user:
        raise Exception('invalid domain id or user id')

    email_addresses = [user.email_address]

    # prepare copy
    email_body = render_email_template(
        template_filename,
        domain_name=domain.name,
        frontend_address=frontend_address
    )

    subject = "You're approved for a new service in the Digital Marketplace"

    send_or_handle_error(
        email_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='evidence assessment approved'
    )


def send_evidence_assessment_rejection_notification(evidence):
    template_filename = 'evidence_assessment_rejected.md'

    frontend_address = current_app.config['FRONTEND_ADDRESS']

    domain = domain_service.find(id=evidence.domain_id).one_or_none()
    user = users.find(id=evidence.user_id).one_or_none()

    if not domain or not user:
        raise Exception('invalid domain id or user id')

    email_addresses = [user.email_address]

    # prepare copy
    email_body = render_email_template(
        template_filename,
        domain_name=domain.name,
        frontend_address=frontend_address
    )

    subject = "Outcome of assessment for %s" % (domain.name)

    send_or_handle_error(
        email_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='evidence assessment approved'
    )
