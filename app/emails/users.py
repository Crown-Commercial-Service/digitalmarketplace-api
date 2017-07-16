# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import six

from flask import current_app, url_for, render_template, session, Response
from app.models import Supplier, Application, User
from dmutils.email import (
    generate_token, EmailError, hash_email, send_email, decode_token, ONE_DAY_IN_SECONDS
)

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


def generate_user_creation_token(name, email_address, **unused):
    data = {
        'name': name,
        'email_address': email_address,
    }
    token = generate_token(data, current_app.config['SECRET_KEY'], current_app.config['USER_INVITE_TOKEN_SALT'])
    return token


def send_account_activation_email(name, email_address, user_type):
    token = generate_user_creation_token(name=name, email_address=email_address)
    if user_type == 'seller':
        url = '{}/sellers/signup/create-user/{}'.format(
            current_app.config['FRONTEND_ADDRESS'],
            token
        )
    else:
        url = '{}/buyers/signup/create/{}'.format(
            current_app.config['FRONTEND_ADDRESS'],
            token
        )

    email_body = render_email_template('create_user_email.md', url=url)

    try:
        send_email(
            email_address,
            email_body,
            current_app.config['INVITE_EMAIL_SUBJECT'],
            current_app.config['INVITE_EMAIL_FROM'],
            current_app.config['INVITE_EMAIL_NAME'],
        )
        session['email_sent_to'] = email_address

    except EmailError as e:
        rollbar.report_exc_info()
        current_app.logger.error(
            'Invitation email failed to send. '
            'error {error} email_hash {email_hash}',
            extra={
                'error': six.text_type(e),
                'email_hash': hash_email(email_address)})
