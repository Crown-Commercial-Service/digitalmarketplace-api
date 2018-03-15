from __future__ import \
    unicode_literals, \
    absolute_import

from . import celery
from flask import current_app
from mailchimp3 import MailChimp
from app.models import Brief, Supplier, SupplierFramework, SupplierDomain, User, Framework, AuditEvent
from dmapiclient.audit import AuditTypes
from app import db
from requests.utils import default_headers
from requests.exceptions import RequestException
from sqlalchemy import true
from os import getenv
from jinja2 import Environment, PackageLoader, select_autoescape
import pendulum


class MailChimpConfigException(Exception):
    """Raised when the MailChimp config is invalid."""


def get_client():
    headers = default_headers()
    headers['User-Agent'] = 'Digital Marketplace (marketplace.service.gov.au)'
    client = MailChimp(
        getenv('MAILCHIMP_USERNAME'),
        getenv('MAILCHIMP_SECRET_API_KEY'),
        timeout=30.0,
        request_headers=headers
    )
    return client

template_env = Environment(
    loader=PackageLoader('app.emails', 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)


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
    briefs = (
        db.session.query(Brief)
        .filter(
            Framework.slug == 'digital-marketplace',
            Brief.data['sellerSelector'].astext == 'allSellers',
            Brief.published_at >= last_run_time
        )
        .all()
    )

    if len(briefs) < 1:
        current_app.logger.info('No briefs found for daily seller email - the campaign was not sent')
        return

    # create a campaign
    try:
        today = pendulum.today()
        campaign = client.campaigns.create(
            data={
                'type': 'regular',
                'recipients': {
                    'list_id': list_id
                },
                'settings': {
                    'title': 'New opportunities - DMP sellers %s-%s-%s' % (today.year, today.month, today.day),
                    'subject_line':
                        'New opportunities in the Digital Marketplace' if len(briefs) > 1
                        else 'A new opportunity in the Digital Marketplace',
                    'reply_to': current_app.config.get('GENERIC_CONTACT_EMAIL'),
                    'from_name': 'The Marketplace team'
                }
            }
        )
    except RequestException as e:
        current_app.logger.error("An Mailchimp API error occurred, aborting: %s %s", e, e.response)
        raise e

    # add content to the campaign
    try:
        template = template_env.get_template('mailchimp_new_seller_opportunities.html')
        email_body = template.render(briefs=briefs, current_year=pendulum.today().year)
        client.campaigns.content.update(
            campaign_id=campaign['id'],
            data={
                'html': email_body.encode('utf-8')
            }
        )
    except RequestException as e:
        current_app.logger.error("An Mailchimp API error occurred, aborting: %s %s", e, e.response)
        raise e

    # schedule the campaign to send at least an hour from runtime, rounded up to the nearest 15 minute mark
    try:
        schedule_time = pendulum.now('UTC').add(hours=1)
        current_minute = schedule_time.minute
        if current_minute % 15 != 0:
            new_minute = current_minute
            while new_minute % 15 != 0:
                new_minute = new_minute + 1
            delta = new_minute - current_minute
            schedule_time = schedule_time.add(minutes=delta)

        client.campaigns.actions.schedule(campaign_id=campaign['id'], data={
            'schedule_time': schedule_time
        })
        current_app.logger.info('Scheduled new briefs seller email campaign for %s', schedule_time.isoformat())
    except RequestException as e:
        current_app.logger.error("An Mailchimp API error occurred, aborting: %s %s", e, e.response)
        raise e

    # record the audit event
    audit = AuditEvent(
        audit_type=AuditTypes.send_seller_opportunities_campaign,
        user=None,
        data={
            'briefs_sent': len(briefs)
        },
        db_object=None
    )
    db.session.add(audit)
    db.session.commit()


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
    for new_address in new_addresses:
        try:
            client.lists.members.create(list_id, data={'email_address': new_address, 'status': 'subscribed'})
            current_app.logger.info(
                'An address was added to the Mailchimp list: list_id: %s seller: %s',
                list_id,
                new_address
            )
        except RequestException as e:
            current_app.logger.error("An Mailchimp API error occurred: %s %s", e, e.response)
