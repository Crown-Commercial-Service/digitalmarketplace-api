# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from flask import current_app
from app.models import Supplier, Application, User

from .util import render_email_template, send_or_handle_error


def send_existing_seller_notification(email_address, supplier_code):
    TEMPLATE_FILENAME = 'user_existing_seller.md'

    supplier = Supplier.query.filter(Supplier.code == supplier_code).first()

    # prepare copy
    email_body = render_email_template(
        TEMPLATE_FILENAME,
        business_name=supplier.name,
        representative=supplier.data.get('representative'),
    )

    subject = "Duplicate application"

    send_or_handle_error(
        email_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='signup - existing seller'
    )


def send_existing_application_notification(email_address, application_id):
    TEMPLATE_FILENAME = 'user_existing_application.md'

    application = Application.query.get(application_id)

    business_name = application.data.get('name')
    representative = application.data.get('representative')

    if not business_name:
        TEMPLATE_FILENAME = 'user_existing_application_no_name.md'

    if not representative:
        user = User.query.filter(User.application_id == application_id).first()

        if user:
            representative = user.name

    # prepare copy
    email_body = render_email_template(
        TEMPLATE_FILENAME,
        business_name=business_name,
        representative=representative,
    )

    subject = "Duplicate application"

    send_or_handle_error(
        email_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='signup - existing seller'
    )
