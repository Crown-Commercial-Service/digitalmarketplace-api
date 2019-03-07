from __future__ import absolute_import, unicode_literals

from os import getenv

import pendulum
import rollbar
from flask import current_app
from jinja2 import Environment, PackageLoader, select_autoescape
from mailchimp3 import MailChimp
from requests.exceptions import RequestException
from requests.utils import default_headers
from sqlalchemy import true

from app import db
from app.api.services import AuditTypes as audit_types
from app.api.services import audit_service, audit_types, suppliers, briefs
from app.models import (AuditEvent, Brief, Framework, Supplier, SupplierDomain,
                        SupplierFramework, User)
from dmapiclient.audit import AuditTypes

from . import celery


class MailChimpConfigException(Exception):
    """Raised when the MailChimp config is invalid."""


def get_client():
    headers = default_headers()
    headers['User-Agent'] = 'Digital Marketplace (marketplace.service.gov.au)'
    client = MailChimp(
        getenv('MAILCHIMP_SECRET_API_KEY'),
        getenv('MAILCHIMP_USERNAME'),
        timeout=30.0,
        request_headers=headers
    )
    return client


template_env = Environment(
    loader=PackageLoader('app.emails', 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)


def create_campaign(client, recipients, settings=None):
    if settings is None:
        settings = {}

    settings.update({
        'from_name': 'The Marketplace team',
        'reply_to': current_app.config.get('GENERIC_CONTACT_EMAIL')
    })

    try:
        response = client.campaigns.create(
            data={
                'type': 'regular',
                'recipients': recipients,
                'settings': settings
            }
        )

        current_app.logger.info('Mailchimp campaign {} created with list {}'
                                .format(response['id'], recipients['list_id']))
        return response
    except RequestException as e:
        current_app.logger.error(
            'A Mailchimp API error occurred while creating a campaign, aborting: {} {}'.format(e, e.response))
        rollbar.report_exc_info()
        raise e


def update_campaign_content(client, campaign_id, email_body):
    try:
        response = client.campaigns.content.update(
            campaign_id=campaign_id,
            data={
                'html': email_body.encode('utf-8')
            }
        )

        current_app.logger.info('Content updated for Mailchimp campaign {}'.format(campaign_id))
        return response
    except RequestException as e:
        current_app.logger.error(
            'A Mailchimp API error occurred while updating content for campaign {}, aborting: {} {}'
            .format(campaign_id, e, e.response))
        rollbar.report_exc_info()
        raise e


def schedule_campaign(client, campaign_id, schedule_time):
    try:
        response = client.campaigns.actions.schedule(campaign_id=campaign_id, data={
            'schedule_time': schedule_time
        })
        current_app.logger.info('Mailchimp campaign {} scheduled for {}'.format(campaign_id, schedule_time))
        return response
    except RequestException as e:
        current_app.logger.error(
            'A Mailchimp API error occurred while scheduling campaign {}, aborting: {} {}'
            .format(campaign_id, e, e.response))
        rollbar.report_exc_info()
        raise e


def add_members_to_list(client, list_id, email_addresses):
    try:
        data = {
            'members': [{
                'email_address': email_address,
                'status': 'subscribed'
            } for email_address in email_addresses]
        }

        response = client.lists.update_members(list_id=list_id, data=data)

        current_app.logger.info(
            '{} were added to Mailchimp list {}'.format(', '.join(email_addresses), list_id)
        )

        return response
    except RequestException as e:
        current_app.logger.error(
            'A Mailchimp API error occurred while adding a member to list {}, aborting: {} {}'
            .format(list_id, e, e.response))
        rollbar.report_exc_info()
        raise e


def send_document_expiry_campaign(client, sellers):
    folder_id = getenv('MAILCHIMP_MARKETPLACE_FOLDER_ID')
    if not folder_id:
        raise MailChimpConfigException('Failed to get MAILCHIMP_MARKETPLACE_FOLDER_ID from the environment variables.')

    list_id = getenv('MAILCHIMP_SELLER_LIST_ID')
    if not list_id:
        raise MailChimpConfigException('Failed to get MAILCHIMP_SELLER_LIST_ID from the environment variables.')

    title = 'Expiring documents - {}'.format(pendulum.today().to_date_string())

    sent_expiring_documents_audit_event = audit_service.filter(
        AuditEvent.type == audit_types.sent_expiring_documents_email.value,
        AuditEvent.data['campaign_title'].astext == title
    ).one_or_none()

    if (sent_expiring_documents_audit_event > 0):
        return

    conditions = []
    for seller in sellers:
        for email_address in seller['email_addresses']:
            conditions.append({
                'condition_type': 'EmailAddress',
                'op': 'is',
                'field': 'EMAIL',
                'value': email_address
            })

    recipients = {
        'list_id': list_id,
        'segment_opts': {
            'match': 'any',
            'conditions': conditions
        }
    }

    settings = {
        'folder_id': folder_id,
        'preview_text': 'Please update your documents',
        'subject_line': 'Your documents are soon to expire or have expired',
        'title': title
    }

    campaign = create_campaign(client, recipients, settings)

    template = template_env.get_template('mailchimp_document_expiry.html')
    email_body = template.render(current_year=pendulum.today().year)
    update_campaign_content(client, campaign['id'], email_body)

    schedule_campaign(client, campaign['id'],
                      pendulum.now('Australia/Sydney').at(10, 0, 0).in_timezone('UTC'))

    audit_service.log_audit_event(
        audit_type=audit_types.sent_expiring_documents_email,
        data={
            'campaign_title': title,
            'sellers': sellers
        },
        db_object=None,
        user=None
    )


@celery.task
def send_document_expiry_reminder():
    # Find sellers with documents 28 days from expiry, 14 days from expiry, on expiry and 28 days after expiry
    sellers = (suppliers.get_suppliers_with_expiring_documents(days=28) +
               suppliers.get_suppliers_with_expiring_documents(days=14) +
               suppliers.get_suppliers_with_expiring_documents(days=0) +
               suppliers.get_suppliers_with_expiring_documents(days=-28))

    if not sellers:
        return

    try:
        client = get_client()
        send_document_expiry_campaign(client, sellers)
    except Exception as e:
        current_app.logger.error(
            'An error occurred while creating the expiring documents campaign, aborting: {}'.format(e))
        rollbar.report_exc_info()


@celery.task
def send_new_briefs_email():
    client = get_client()
    list_id = getenv('MAILCHIMP_SELLER_EMAIL_LIST_ID')

    if not list_id:
        raise MailChimpConfigException('Failed to get MAILCHIMP_SELLER_EMAIL_LIST_ID from the environment variables.')

    # determine the age of the briefs being requested, defaulting to 24 hours ago
    last_run_audit = (
        db.session.query(AuditEvent)
        .filter(AuditEvent.type == AuditTypes.send_seller_opportunities_campaign.value)
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    if last_run_audit:
        last_run_time = last_run_audit.created_at
    else:
        last_run_time = pendulum.now().subtract(hours=24)

    # gather the briefs
    open_briefs = briefs.get_open_briefs_published_since(since=last_run_time)
    briefs_atm = [x for x in open_briefs if x.lot.slug == 'atm']
    briefs_professionals = [x for x in open_briefs if x.lot.slug == 'digital-professionals']
    briefs_training = [x for x in open_briefs if x.lot.slug == 'training']

    if len(open_briefs) < 1:
        current_app.logger.info('No briefs found for daily seller email - the campaign was not sent')
        return

    # create a campaign
    today = pendulum.today()
    recipients = {
        'list_id': list_id
    }
    campaign = create_campaign(client, recipients, {
        'subject_line': 'New opportunities in the Digital Marketplace' if len(open_briefs) > 1
                        else 'A new opportunity in the Digital Marketplace',
        'title': 'New opportunities - DMP sellers %s-%s-%s' % (today.year, today.month, today.day)
    })

    # add content to the campaign
    template = template_env.get_template('mailchimp_new_seller_opportunities.html')
    email_body = template.render(
        brief_count=len(open_briefs),
        briefs_atm=briefs_atm,
        briefs_professionals=briefs_professionals,
        briefs_training=briefs_training,
        current_year=pendulum.today().year
    )
    update_campaign_content(client, campaign['id'], email_body)

    # schedule the campaign to send at least an hour from runtime, rounded up to the nearest 15 minute mark
    schedule_time = pendulum.now('UTC').add(hours=1)
    current_minute = schedule_time.minute
    if current_minute % 15 != 0:
        new_minute = current_minute
        while new_minute % 15 != 0:
            new_minute = new_minute + 1
        delta = new_minute - current_minute
        schedule_time = schedule_time.add(minutes=delta)

    schedule_campaign(client, campaign['id'], schedule_time)

    # record the audit event
    try:
        audit = AuditEvent(
            audit_type=AuditTypes.send_seller_opportunities_campaign,
            user=None,
            data={
                'briefs_sent': len(open_briefs),
                'email_body': email_body
            },
            db_object=None
        )
        db.session.add(audit)
        db.session.commit()
    except Exception:
        rollbar.report_exc_info()


@celery.task
def sync_mailchimp_seller_list():
    client = get_client()
    list_id = getenv('MAILCHIMP_SELLER_LIST_ID')

    if not list_id:
        raise MailChimpConfigException('Failed to get MAILCHIMP_SELLER_LIST_ID from the environment variables.')

    # get the mailchimp list's existing members
    try:
        current_members = client.lists.members.all(
            list_id,
            fields='members.email_address,members.id',
            get_all=True
        )
    except RequestException as e:
        current_app.logger.error("An Mailchimp API error occurred, aborting: %s %s", e, e.response)
        raise e

    current_member_addresses = []
    try:
        for member in current_members['members']:
            current_member_addresses.append(member['email_address'].lower())
    except KeyError:
        pass

    # get the addresses from DM service supplier users
    sub1 = db.session.query(SupplierFramework.supplier_code)\
        .filter(Framework.slug == 'digital-marketplace')\
        .join(Framework)
    sub2 = db.session.query(SupplierDomain.supplier_id)
    sub3 = db.session.query(Supplier.code)\
        .filter(Supplier.status != 'deleted', Supplier.code.in_(sub1), Supplier.id.in_(sub2))
    results = db.session.query(User.email_address)\
        .filter(User.role == 'supplier', User.active == true(), User.supplier_code.in_(sub3))\
        .all()

    supplier_users = [x[0].lower() for x in results]

    # get the contact addresses for DM service suppliers
    sub1 = db.session.query(SupplierFramework.supplier_code)\
        .filter(Framework.slug == 'digital-marketplace')\
        .join(Framework)
    sub2 = db.session.query(SupplierDomain.supplier_id)
    results = db.session.query(Supplier.data['contact_email'], Supplier.id)\
        .filter(Supplier.code.in_(sub1), Supplier.id.in_(sub2), Supplier.status != 'deleted')\
        .order_by(Supplier.id)\
        .all()

    supplier_contacts = [x[0].lower() for x in results]

    # combine the user and supplier contact lists
    combined_supplier_addresses = [x for x in supplier_contacts if x not in supplier_users]
    combined_supplier_addresses = combined_supplier_addresses + supplier_users

    # get the suppliers not in the mailchimp list
    new_addresses = [
        x for x in combined_supplier_addresses if x not in current_member_addresses
    ]

    # add the new suppliers to the mailchimp list
    add_members_to_list(client, list_id, new_addresses)
