"""

Usage:
    scripts/generate-user-email-list.py <data_api_url> <data_api_token> [--framework=<slug>]
"""
import csv
import sys
import multiprocessing
from multiprocessing.pool import ThreadPool

from docopt import docopt
from dmutils.apiclient import DataAPIClient
from dmutils.audit import AuditTypes


def is_registered_with_framework(client, framework_id):
    def is_of_framework(audit):
        return audit['data'].get('frameworkSlug') == framework_id

    def is_registered(user):
        audits = client.find_audit_events(
            audit_type=AuditTypes.register_framework_interest,
            object_type='suppliers',
            object_id=user['supplier']['supplierId'])
        return any(map(is_of_framework, audits['auditEvents'])), user
    return is_registered


def filter_is_registered_with_framework(client, framework_id, users):
    pool = ThreadPool(10)
    is_registered = is_registered_with_framework(client, framework_id)
    return (
        user for good, user
        in pool.imap_unordered(is_registered, users)
        if good)


def find_supplier_users(client):
    for user in client.find_users_iter():
        if user['active'] and user['role'] == 'supplier':
            yield user


def generate_user_email_list(data_api_url, data_api_token, framework_slug):
    client = DataAPIClient(data_api_url, data_api_token)

    writer = csv.writer(sys.stdout, delimiter=',', quotechar='"')

    users = find_supplier_users(client)
    if framework_slug is not None:
        users = filter_is_registered_with_framework(client, framework_slug, users)

    for user in users:
        writer.writerow([
            user['emailAddress'].encode('utf-8'),
            user['name'].encode('utf-8'),
            user['supplier']['supplierId'],
            user['supplier']['name'].encode('utf-8')])


if __name__ == '__main__':
    arguments = docopt(__doc__)

    generate_user_email_list(
        data_api_url=arguments['<data_api_url>'],
        data_api_token=arguments['<data_api_token>'],
        framework_slug=arguments.get('--framework'))
