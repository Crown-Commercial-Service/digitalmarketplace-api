# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from flask import current_app

from .util import render_email_template, send_or_handle_error

import rollbar


def send_brief_response_received_email(supplier, brief, brief_response):
    if brief.lot.slug == 'digital-outcome':
        TEMPLATE_FILENAME = 'brief_response_submitted_outcome.md'
    elif brief.lot.slug == 'training':
        TEMPLATE_FILENAME = 'brief_response_submitted_training.md'
    elif brief.lot.slug == 'rfx':
        TEMPLATE_FILENAME = 'brief_response_submitted_rfx.md'
    else:
        TEMPLATE_FILENAME = 'brief_response_submitted.md'

    to_address = brief_response.data['respondToEmailAddress']
    specialist_name = brief_response.data.get('specialistName', None)

    if brief.lot.slug == 'rfx':
        brief_url = current_app.config['FRONTEND_ADDRESS'] + '/2/' + brief.framework.slug + '/opportunities/' \
            + str(brief.id)
    else:
        brief_url = current_app.config['FRONTEND_ADDRESS'] + '/' + brief.framework.slug + '/opportunities/' \
            + str(brief.id)
    attachment_url = current_app.config['FRONTEND_ADDRESS'] +\
        '/api/2/brief/' + str(brief.id) + '/respond/documents/' + str(supplier.code) + '/'

    ess = ""
    if brief_response.data.get('essentialRequirements', None):
        i = 0
        for req in brief.data['essentialRequirements']:
            ess += "####• {}\n{}\n\n".format(req, brief_response.data['essentialRequirements'][i])
            i += 1
    nth = ""
    if brief_response.data.get('niceToHaveRequirements', None):
        i = 0
        for req in brief.data['niceToHaveRequirements']:
            nth += "####• {}\n{}\n\n".format(
                req,
                brief_response.data.get('niceToHaveRequirements', [])[i]
                if i < len(brief_response.data.get('niceToHaveRequirements', [])) else ''
            )
            i += 1

    attachments = ""
    for attch in brief_response.data.get('attachedDocumentURL', []):
        attachments += "####• [{}]({}{})\n\n".format(attch, attachment_url, attch)

    subject = "We've received your application"
    response_title = "How you responded"
    if specialist_name:
        subject = "{}'s application for opportunity ID {} has been received".format(specialist_name, brief.id)
        response_title = "{}'s responses".format(specialist_name)

    # prepare copy
    email_body = render_email_template(
        TEMPLATE_FILENAME,
        brief_url=brief_url,
        brief_name=brief.data['title'],
        essential_requirements=ess,
        nice_to_have_requirements=nth,
        attachments=attachments,
        closing_at=brief.closed_at.to_formatted_date_string(),
        specialist_name=specialist_name,
        response_title=response_title,
        brief_response=brief_response.data,
        header='<div style="font-size: 1.8rem">'
               '<span style="color: #007554;padding-right: 1rem;">✔</span>'
               '<span>{}</span></div>'.format(subject)
    )

    send_or_handle_error(
        to_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='brief response recieved'
    )


def send_brief_closed_email(brief):
    from app.api.services import audit_service, audit_types  # to circumvent circular dependency

    brief_email_sent_audit_event = audit_service.find(type=audit_types.sent_closed_brief_email.value,
                                                      object_type="Brief",
                                                      object_id=brief.id).count()

    if (brief_email_sent_audit_event > 0):
        return

    to_addresses = [user.email_address for user in brief.users if user.active]

    # prepare copy
    email_body = render_email_template(
        'brief_closed.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        brief_name=brief.data['title'],
        brief_id=brief.id
    )

    subject = "Your brief has closed - please review all responses."

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='brief closed'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.sent_closed_brief_email,
        user='',
        data={
            "to_addresses": ', '.join(to_addresses),
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief)


def send_seller_requested_feedback_from_buyer_email(brief):
    from app.api.services import audit_service, audit_types  # to circumvent circular dependency

    to_addresses = [user.email_address for user in brief.users if user.active]

    # prepare copy
    email_body = render_email_template(
        'seller_requested_feedback_from_buyer_email.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        brief_name=brief.data['title'],
        brief_id=brief.id
    )

    subject = "Buyer notifications to unsuccessful sellers"

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='seller_requested_feedback_from_buyer_email'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.seller_requested_feedback_from_buyer_email,
        user='',
        data={
            "to_addresses": ', '.join(to_addresses),
            "email_body": email_body,
            "subject": subject
        },
        db_object=brief)


def send_seller_invited_to_rfx_email(brief, invited_supplier):
    from app.api.services import audit_service, audit_types  # to circumvent circular dependency

    to_addresses = []
    if 'contact_email' in invited_supplier.data:
        to_addresses = [invited_supplier.data['contact_email']]
    elif 'email' in invited_supplier.data:
        to_addresses = [invited_supplier.data['email']]

    if len(to_addresses) > 0:
        email_body = render_email_template(
            'brief_rfx_invite_seller.md',
            frontend_url=current_app.config['FRONTEND_ADDRESS'],
            brief_name=brief.data['title'],
            brief_id=brief.id
        )

        subject = "You have been invited to respond to an opportunity"

        send_or_handle_error(
            to_addresses,
            email_body,
            subject,
            current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
            current_app.config['DM_GENERIC_SUPPORT_NAME'],
            event_description_for_errors='seller_invited_to_rfx_opportunity'
        )

        audit_service.log_audit_event(
            audit_type=audit_types.seller_invited_to_rfx_opportunity,
            user='',
            data={
                "to_addresses": ', '.join(to_addresses),
                "email_body": email_body,
                "subject": subject
            },
            db_object=brief)
