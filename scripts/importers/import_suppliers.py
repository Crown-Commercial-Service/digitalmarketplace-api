#!/usr/bin/env python2

#  Example usage:
#  ./scripts/importers/import_suppliers.py http://data-api.example.com/ < 'example_listings/test_source_data/DMP Data Source - Test data.csv'  # noqa
import csv
import json
import os
import re
import sys
import urllib2
import urlparse
import logging


def nonEmptyOrNone(s):
    """
    Converts empty strings to None.

    Needed because CSV format doesn't know the difference.
    Used when strings should not be empty, and empty source data means unknown.
    """
    if s:
        return s
    return None


def run_import(input_file, client):
    num_failures = 0
    num_successes = 0

    for record in csv.DictReader(input_file):
        if not record['ID']:
            continue

        display_name = record.get('Display name', None)
        if display_name:
            name = display_name
            long_name = record['Name']
        else:
            name = record['Name']
            long_name = None

        website = record.get('Website', None)
        if not website or re.match('https?://', website) is None:
            # Clean up empty strings and variations of 'n/a', 'none', etc
            website = None

        linkedin_url = record.get('LinkedIn', None)
        # This field sometimes contains variations of 'Not listed'
        if linkedin_url and 'www.linkedin.com' in linkedin_url:
            extra_links = [{
                'url': linkedin_url,
                'label': 'LinkedIn',
            }]
        else:
            extra_links = []

        supplier = {
            'code': record['ID'],
            'name': name,
            'longName': long_name,
            'summary': nonEmptyOrNone(record['Summary']),
            'abn': nonEmptyOrNone(record['ABN']),
            'website': website,
            'address': {
                'addressLine': nonEmptyOrNone(record['Address']),
                'suburb': nonEmptyOrNone(record['Suburb']),
                'state': record['State'],
                'postalCode': record['PCode'],
            },
            'contacts': [{
                'name': record['Contact Name'],
                'role': nonEmptyOrNone(record['Title']),  # sic
                'email': nonEmptyOrNone(record['Email address']),
                'phone': nonEmptyOrNone(record['Phone']),
                'fax': nonEmptyOrNone(record['fax']),
            }]
        }

        response = client.post('/suppliers', data=json.dumps({'supplier': supplier}), content_type='application/json')
        if response.status_code >= 400:
            num_failures += 1
            msg = 'Error adding supplier {}: server returned code {} {}'.format(
                supplier['code'],
                response.status_code,
                response.get_data()
            )
            logging.error(msg)
        else:
            num_successes += 1

    return num_failures, num_successes


class Response(object):

    def __init__(self, code, data):
        self.status_code = code
        self.data = data

    def get_data(self):
        return self.data


class Client(object):

    def __init__(self, api_host, api_token):
        self.api_host = api_host
        self.headers = {'Authorization': 'Bearer {}'.format(api_token)}

    def post(self, path, data, content_type='application/json'):
        api_url = urlparse.urljoin(self.api_host, path)

        headers = self.headers.copy()
        headers['Content-Type'] = content_type
        request = urllib2.Request(api_url, data, self.headers)

        try:
            result = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            return Response(e.code, e.fp.read())
        return Response(result.code, result.read())


if __name__ == '__main__':
    api_token = os.environ.get('DM_DATA_API_AUTH_TOKEN')
    if len(sys.argv) > 1:
        api_host = sys.argv[1]
    else:
        api_host = 'http://localhost:5000/'

    client = Client(api_host, api_token)

    num_failures, num_successes = run_import(sys.stdin, client)
    if num_failures > 0:
        sys.exit(1)
