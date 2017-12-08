# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import pendulum
from flask import current_app
from flask_login import current_user
from app.models import Supplier

from .util import render_email_template, send_or_handle_error


def send_price_change_email(prices):
    TEMPLATE_FILENAME = 'price_changes.md'
    FRONTEND_ADDRESS = current_app.config['FRONTEND_ADDRESS']

    supplier = Supplier.query.filter(Supplier.code == current_user.supplier_code).first()

    prices_markdown = ''.join('- {} {} in {} {} was changed from ${} to ${} starting on {} {}\n'
                              .format(p[0].service_type.name,
                                      '(' + p[0].service_sub_type.name + ')' if p[0].service_sub_type.name else '',
                                      p[0].region.state, p[0].region.name, p[0].price, p[1].price, p[1].date_from,
                                      'until ' + str(p[1].date_to) if p[1].date_to != pendulum.Date(2050, 1, 1) else '')
                              for p in prices)

    email_body = render_email_template(
        TEMPLATE_FILENAME,
        supplier_name=supplier.name,
        price_changes=prices_markdown,
        update_timestamp=pendulum.now(current_app.config['DEADLINES_TZ_NAME']).to_datetime_string(),
        user_name=current_user.name,
        login_url='{}/orams/login'.format(FRONTEND_ADDRESS)
    )

    subject = "ORAMS Price Change"

    send_or_handle_error(
        [current_user.email_address, current_app.config['ORAMS_BUYER_INVITE_REQUEST_ADMIN_EMAIL']],
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['ORAMS_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='orams price change'
    )
