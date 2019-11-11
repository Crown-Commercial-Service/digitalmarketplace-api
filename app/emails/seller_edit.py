# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from urllib import quote_plus

import pendulum
import rollbar
import six
from flask import current_app, session

from app.api.business.agreement_business import (get_current_agreement,
                                                 get_new_agreement)
from app.api.helpers import get_root_url
from dmutils.email import EmailError, hash_email

from .util import escape_markdown, render_email_template, send_or_handle_error


def send_notify_auth_rep_email(supplier_code):
    from app.api.services import (
        audit_service,
        audit_types,
        suppliers,
        key_values_service
    )

    supplier = suppliers.get_supplier_by_code(supplier_code)
    to_address = supplier.data.get('email', '').encode('utf-8')

    agreement = get_new_agreement()
    if agreement is None:
        agreement = get_current_agreement()

    start_date = pendulum.now('Australia/Canberra').date()
    if agreement:
        start_date = agreement.start_date.in_tz('Australia/Canberra')

    # prepare copy
    email_body = render_email_template(
        'seller_edit_notify_auth_rep.md',
        ma_start_date=start_date.strftime('%-d %B %Y'),
        supplier_name=supplier.name,
        supplier_code=supplier.code,
        auth_rep_name=escape_markdown(supplier.data.get('representative', '')),
        frontend_url=current_app.config['FRONTEND_ADDRESS']
    )

    subject = "Accept the Master Agreement for the Digital Marketplace"

    send_or_handle_error(
        to_address,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='notify auth rep email'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.notify_auth_rep_accept_master_agreement,
        user='',
        data={
            "to_address": to_address,
            "email_body": email_body,
            "subject": subject
        },
        db_object=supplier)


def send_decline_master_agreement_email(supplier_code):
    from app.api.services import (
        audit_service,
        audit_types,
        suppliers
    )

    supplier = suppliers.get_supplier_by_code(supplier_code)
    to_addresses = [
        e['email_address']
        for e in suppliers.get_supplier_contacts(supplier_code)
    ]

    # prepare copy
    email_body = render_email_template(
        'seller_edit_decline.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS']
    )

    subject = "You declined the new Master Agreement"

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='declined master agreement email'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.declined_master_agreement_email,
        user='',
        data={
            "to_address": to_addresses,
            "email_body": email_body,
            "subject": subject
        },
        db_object=supplier)


def send_team_member_account_activation_email(token, email_address, framework, user_name, supplier_name):
    url = '{}{}/create-user/{}?e={}'.format(
        current_app.config['FRONTEND_ADDRESS'],
        get_root_url(framework),
        token,
        quote_plus(email_address)
    )

    email_body = render_email_template(
        'seller_edit_team_member_create_user_email.md',
        url=url,
        user_name=user_name,
        supplier_name=supplier_name,
        frontend_url=current_app.config['FRONTEND_ADDRESS']
    )

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
