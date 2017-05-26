# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from flask import current_app
from app.models import Application, User, Supplier, Domain

from .util import render_email_template, send_or_handle_error


def send_submitted_existing_seller_notification(application_id):
    TEMPLATE_FILENAME = 'application_submitted_existing_seller.md'

    FRONTEND_ADDRESS = current_app.config['FRONTEND_ADDRESS']

    application = Application.query.get(application_id)

    to_address = application.data['email']

    url_sellers_guide = FRONTEND_ADDRESS + '/sellers-guide'

    # prepare copy
    email_body = render_email_template(
        TEMPLATE_FILENAME,
        business_name=application.supplier.name,
        contact_name=application.data['contact_name'],
        url_sellers_guide=url_sellers_guide
    )

    subject = "Digital Marketplace profile update application received"

    send_or_handle_error(
        to_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='application submitted - existing seller'
    )


def send_submitted_new_seller_notification(application_id):
    TEMPLATE_FILENAME = 'application_submitted_new_seller.md'

    FRONTEND_ADDRESS = current_app.config['FRONTEND_ADDRESS']

    application = Application.query.get(application_id)

    to_address = application.data['email']

    url_sellers_guide = FRONTEND_ADDRESS + '/sellers-guide'

    # prepare copy
    email_body = render_email_template(
        TEMPLATE_FILENAME,
        business_name=application.data['name'],
        contact_name=application.data['contact_name'],
        url_sellers_guide=url_sellers_guide
    )

    subject = "Thanks for your Digital Marketplace application"

    send_or_handle_error(
        to_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='application submitted - new seller'
    )


def send_approval_notification(application_id):

    FRONTEND_ADDRESS = current_app.config['FRONTEND_ADDRESS']

    application = Application.query.get(application_id)

    if len(application.supplier.legacy_domains) > 0:
        TEMPLATE_FILENAME = 'application_approved_existing_seller.md'
        subject = "Your updated profile is live"
    else:
        TEMPLATE_FILENAME = 'application_approved_new_seller.md'
        subject = "You’re now listed in the Digital Marketplace"

    to_address = application.supplier.contacts[0].email

    url_sellers_guide = FRONTEND_ADDRESS + '/sellers-guide'
    url_assessments = FRONTEND_ADDRESS + '/sellers-guide#assessments'
    url_latest_opportunities = FRONTEND_ADDRESS + '/digital-service-professionals/opportunities'
    url_seller_page = FRONTEND_ADDRESS + '/supplier/' + str(application.supplier.code)

    # prepare copy
    email_body = render_email_template(
        TEMPLATE_FILENAME,
        business_name=application.supplier.name,
        url_assessments=url_assessments,
        url_sellers_guide=url_sellers_guide,
        url_latest_opportunities=url_latest_opportunities,
        url_seller_page=url_seller_page
    )

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


def send_assessment_approval_notification(supplier_id, domain_id):
    TEMPLATE_FILENAME = 'assessment_approved.md'

    FRONTEND_ADDRESS = current_app.config['FRONTEND_ADDRESS']

    supplier = Supplier.query.get(supplier_id)
    domain = Domain.query.get(domain_id)

    users = User.query.filter(User.supplier_code == supplier.code).all()

    email_addresses = [u.email_address for u in users]
    url_latest_opportunities = FRONTEND_ADDRESS + '/digital-service-professionals/opportunities'
    url_seller_page = FRONTEND_ADDRESS + '/supplier/' + str(supplier.code)

    # prepare copy
    email_body = render_email_template(
        TEMPLATE_FILENAME,
        business_name=supplier.name,
        domain_name=domain.name,
        url_latest_opportunities=url_latest_opportunities,
        url_seller_page=url_seller_page
    )

    subject = "You’re approved for a new service in the Digital Marketplace"

    send_or_handle_error(
        email_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='assessment approved'
    )


def send_revert_notification(application_id, message):
    TEMPLATE_FILENAME = 'application_reverted.md'

    application = Application.query.get(application_id)
    to_address = application.data['email']
    email_addresses = [to_address, current_app.config['GENERIC_CONTACT_EMAIL']]

    email_body = render_email_template(
        TEMPLATE_FILENAME,
        reversion_message=message
    )

    subject = "Digital Marketplace application changes requested"

    send_or_handle_error(
        email_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='Application reversion notification email'
    )
