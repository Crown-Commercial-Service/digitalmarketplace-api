# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import six

from flask import current_app, session, jsonify
from urllib import quote_plus
from app.models import Supplier, Application, User
from dmutils.email import EmailError, hash_email
import rollbar

from .util import render_email_template, send_or_handle_error, escape_markdown
from urllib import quote


def get_root_url(framework_slug):
    return current_app.config['APP_ROOT'].get(framework_slug)


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


def send_account_activation_email(token, email_address, framework):
    url = '{}{}/create-user/{}?e={}'.format(
        current_app.config['FRONTEND_ADDRESS'],
        get_root_url(framework),
        token,
        quote_plus(email_address)
    )

    email_body = render_email_template('create_user_email.md', url=url)

    try:
        send_or_handle_error(
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


def send_user_existing_password_reset_email(name, email_address):
    frontend_url = current_app.config['FRONTEND_ADDRESS']
    email_body = render_email_template(
        'user_existing_password_reset.md',
        frontend_url=frontend_url,
        name=name,
        reset_password_url='{}/2/reset-password'.format(frontend_url)
    )

    try:
        send_or_handle_error(
            email_address,
            email_body,
            'You are already registered',
            current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
            current_app.config['DM_GENERIC_SUPPORT_NAME']
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


def send_account_activation_manager_email(token, manager_name, manager_email, applicant_name, applicant_email,
                                          framework):
    _send_account_activation_admin_email(
        token=token,
        manager_name=manager_name,
        manager_email=manager_email,
        applicant_name=applicant_name,
        applicant_email=applicant_email,
        framework=framework
    )

    email_body = render_email_template(
        'buyer_account_invite_manager_confirmation.md',
        manager_name=escape_markdown(manager_name),
        applicant_name=escape_markdown(applicant_name),
    )

    try:
        send_or_handle_error(
            manager_email,
            email_body,
            current_app.config['BUYER_INVITE_MANAGER_CONFIRMATION_SUBJECT'],
            current_app.config['INVITE_EMAIL_FROM'],
            current_app.config['INVITE_EMAIL_NAME'],
        )
        session['email_sent_to'] = manager_email

    except EmailError as e:
        rollbar.report_exc_info()
        current_app.logger.error(
            'Invitation email to manager failed to send. '
            'error {error} email_hash {email_hash}',
            extra={
                'error': six.text_type(e),
                'email_hash': hash_email(manager_email)})


def _send_account_activation_admin_email(token, manager_name, manager_email, applicant_name, applicant_email,
                                         framework):
    url = '{}{}/send-invite/{}?e={}'.format(
        current_app.config['FRONTEND_ADDRESS'],
        get_root_url(framework),
        token,
        quote_plus(applicant_email)
    )

    email_body = render_email_template(
        'buyer_account_invite_request_email.md',
        manager_name=escape_markdown(manager_name),
        manager_email=escape_markdown(manager_email),
        applicant_name=escape_markdown(applicant_name),
        applicant_email=escape_markdown(applicant_email),
        invite_url=url
    )

    try:
        send_or_handle_error(
            current_app.config['BUYER_INVITE_REQUEST_ADMIN_EMAIL'],
            email_body,
            current_app.config['BUYER_INVITE_MANAGER_CONFIRMATION_SUBJECT'],
            current_app.config['INVITE_EMAIL_FROM'],
            current_app.config['INVITE_EMAIL_NAME'],
        )
        session['email_sent_to'] = current_app.config['BUYER_INVITE_REQUEST_ADMIN_EMAIL']

    except EmailError as e:
        rollbar.report_exc_info()
        current_app.logger.error(
            'Invitation email to manager failed to send. '
            'error {error} email_hash {email_hash}',
            extra={
                'error': six.text_type(e),
                'email_hash': hash_email(manager_email)})


def send_new_user_onboarding_email(name, email_address, user_type, framework):
    if user_type != 'buyer':
        return False

    assert user_type == 'buyer'

    email_body = render_email_template(
        'buyer_onboarding.md',
        name=name,
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
    )

    try:
        send_or_handle_error(
            email_address,
            email_body,
            'Welcome to the Digital Marketplace',
            current_app.config['RESET_PASSWORD_EMAIL_FROM'],
            current_app.config['RESET_PASSWORD_EMAIL_NAME'],
        )
        session['email_sent_to'] = email_address
    except EmailError as error:
        rollbar.report_exc_info()
        current_app.logger.error(
            'buyeronboarding.fail: Buyer onboarding email failed to send. '
            'error {error} email_hash {email_hash}',
            extra={
                'error': six.text_type(error),
                'email_hash': hash_email(email_address)})
        return jsonify(message='Failed to send buyer onboarding email.'), 503


def send_reset_password_confirm_email(token, email_address, locked, framework):
    url = '{}{}/reset-password/{}?e={}'.format(
        current_app.config['FRONTEND_ADDRESS'],
        get_root_url(framework),
        token,
        quote_plus(email_address)
    )
    subject = current_app.config['RESET_PASSWORD_EMAIL_SUBJECT']
    name = current_app.config['RESET_PASSWORD_EMAIL_NAME']
    if locked:
        email_template = 'reset_password_email_locked_account_marketplace.md'
    else:
        email_template = 'reset_password_email_marketplace.md'

    email_body = render_email_template(
        email_template,
        url=url
    )

    try:
        send_or_handle_error(
            email_address,
            email_body,
            subject,
            current_app.config['RESET_PASSWORD_EMAIL_FROM'],
            name
        )
        session['email_sent_to'] = email_address

    except EmailError as e:
        rollbar.report_exc_info()
        current_app.logger.error(
            'Password reset email failed to send. '
            'error {error} email_hash {email_hash}',
            extra={
                'error': six.text_type(e),
                'email_hash': hash_email(email_address)})
