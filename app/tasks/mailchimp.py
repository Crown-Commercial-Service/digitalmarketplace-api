from __future__ import \
    unicode_literals, \
    absolute_import

from . import celery
from flask import current_app
from mailchimp3 import MailChimp
from app.api.suppliers import remove
from app.models import Supplier, SupplierFramework, SupplierDomain, User, Framework
from app import db
from itertools import groupby
from operator import itemgetter
from requests.utils import default_headers
from requests.exceptions import RequestException
from sqlalchemy.orm.util import aliased
from sqlalchemy import true
from sqlalchemy.exc import SQLAlchemyError
from os import getenv
import time


class MailChimpConfigException(Exception):
    """Raised when the MailChimp config is invalid."""


def get_client():
    headers = default_headers()
    headers['User-Agent'] = 'Digital Marketplace (marketplace.service.gov.au)'
    client = MailChimp(
        getenv('MAILCHIMP_USERNAME'),
        getenv('MAILCHIMP_SECRET_API_KEY'),
        timeout=10.0,
        request_headers=headers
    )
    return client


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
        current_app.logger.error("An Mailchimp API error occurred, aborting: %s %s", e, e.response.text)
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
            current_app.logger.error("An Mailchimp API error occurred: %s %s", e, e.response.text)
