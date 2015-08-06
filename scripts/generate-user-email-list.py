"""

Usage:
    scripts/generate-user-email-list.py <data_api_url> <data_api_token>
"""
import csv
import sys

from docopt import docopt
from dmutils.apiclient import DataAPIClient


def generate_user_email_list(data_api_url, data_api_token):
    client = DataAPIClient(data_api_url, data_api_token)

    writer = csv.writer(sys.stdout, delimiter=',', quotechar='"')

    for user in client.find_users_iter():
        if user['active'] and user['role'] == 'supplier':
            writer.writerow([
                user['emailAddress'].encode('utf-8'),
                user['name'].encode('utf-8'),
                user['supplier']['supplierId'],
                user['supplier']['name'].encode('utf-8')])


if __name__ == '__main__':
    arguments = docopt(__doc__)

    generate_user_email_list(
        data_api_url=arguments['<data_api_url>'],
        data_api_token=arguments['<data_api_token>'])
