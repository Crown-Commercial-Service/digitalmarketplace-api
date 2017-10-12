# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from flask import current_app

from .util import render_email_template, send_or_handle_error


def send_brief_response_received_email(supplier, brief, brief_response):
    TEMPLATE_FILENAME = 'brief_response_submitted_outcome.md' if brief.lot.slug == 'digital-outcome' \
        else 'brief_response_submitted.md'

    to_address = brief_response.data['respondToEmailAddress']

    brief_url = current_app.config['FRONTEND_ADDRESS'] + '/' + brief.framework.slug + '/opportunities/' + str(brief.id)
    attachment_url = current_app.config['FRONTEND_ADDRESS'] +\
        '/api/2/brief/' + str(brief.id) + '/respond/documents/' + str(supplier.code) + '/'

    ess = ""
    i = 0
    for req in brief.data['essentialRequirements']:
        ess += "####• {}\n{}\n\n".format(req, brief_response.data['essentialRequirements'][i])
        i += 1
    nth = ""
    i = 0
    for req in brief.data['niceToHaveRequirements']:
        nth += "####• {}\n{}\n\n".format(req, brief_response.data.get('niceToHaveRequirements', [])[i]
                                           if i < len(brief_response.data.get('niceToHaveRequirements', [])) else '')
        i += 1

    attachments = ""
    for attch in brief_response.data.get('attachedDocumentURL'):
        attachments += "####• [{}]({}{})\n\n".format(attch, attachment_url, attch)
    # prepare copy
    email_body = render_email_template(
        TEMPLATE_FILENAME,
        brief_url=brief_url,
        brief_name=brief.data['title'],
        essential_requirements=ess,
        nice_to_have_requirements=nth,
        attachments=attachments,
        brief_response=brief_response.data,
        header='<div style="padding: 0rem; border: 2px solid #007554; font-size: 2rem;">'
               '<p style="background: white; margin: 0;"><span style="background: #007554; padding: 1rem; '
               'display: inline-block; line-height: 2rem; width: 3rem; margin-right: 1rem;">'
               '<span style="text-align: center; width: 2rem; background: white; padding: 0.5rem; '
               'display: inline-block; color: #007554; border-radius: 2rem;">✔</span>'
               '</span>We\'ve received your application.</div>'
    )

    subject = "We've received your application"

    send_or_handle_error(
        to_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='brief response recieved'
    )
