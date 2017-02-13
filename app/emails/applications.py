# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from flask import current_app
from app.models import Application

from .util import render_email_template, send_or_handle_error


def send_approval_notification(application_id):
    TEMPLATE_FILENAME = 'application_approved.md'

    FRONTEND_ADDRESS = current_app.config['FRONTEND_ADDRESS']

    application = Application.query.get(application_id)

    to_address = application.supplier.contacts[0].email

    url_sellers_guide = FRONTEND_ADDRESS + '/sellers-guide'
    url_latest_opportunities = FRONTEND_ADDRESS + '/digital-service-professionals/opportunities'
    url_seller_page = FRONTEND_ADDRESS + '/supplier/' + str(application.supplier.code)

    # prepare copy
    email_body = render_email_template(
        TEMPLATE_FILENAME,
        business_name=application.supplier.name,
        url_sellers_guide=url_sellers_guide,
        url_latest_opportunities=url_latest_opportunities,
        url_seller_page=url_seller_page
    )

    subject = "You’re now listed in the Digital Marketplace"

    send_or_handle_error(
        to_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='application approved'
    )


def send_rejection_notification(application_id):
    TEMPLATE_FILENAME = 'application_rejected.md'

    FRONTEND_ADDRESS = current_app.config['FRONTEND_ADDRESS']

    application = Application.query.get(application_id)
    to_address = application.data['email']

    # prepare copy
    email_body = render_email_template(
        TEMPLATE_FILENAME,
        contact_name=application.data['contact_name']
    )

    subject = "There was a problem with your Digital Marketplace application"

    send_or_handle_error(
        to_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='application rejected'
    )
