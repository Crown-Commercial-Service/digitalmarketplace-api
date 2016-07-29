#!/usr/bin/env python2

#  Example usage:
#  ./scripts/importers/import_suppliers.py http://data-api.example.com/ < 'example_listings/test_source_data/DMP Data Source - Test data.csv'  # noqa
import csv
import json
import re
import logging

from utils import nonEmptyOrNone, makeClient


def run_import(input_file, client):
    num_failures = 0
    num_successes = 0

    for record in csv.DictReader(input_file):
        if not record['ID']:
            continue

        if record['Ready to upload'] != 'Y':
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
            'extraLinks': extra_links,
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


if __name__ == '__main__':
    import sys
    client = makeClient()

    num_failures, num_successes = run_import(sys.stdin, client)
    if num_failures > 0:
        sys.exit(1)
