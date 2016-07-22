#!/usr/bin/env python2

#  Example usage:
#  ./scripts/importers/import_suppliers.py http://data-api.example.com/ < 'example_listings/test_source_data/DMP Data Source - Test data.csv'
import csv
import json
import os
import re
import sys
import urllib2
import logging


api_token = os.environ.get('DM_DATA_API_AUTH_TOKEN')
if len(sys.argv) > 1:
    api_host = sys.argv[1]
else:
    api_host = 'http://localhost:5000/'
api_url = '{}suppliers'.format(api_host)

headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer {}'.format(api_token)
}

def nonEmptyOrNone(s):
    """
    Converts empty strings to None.

    Needed because CSV format doesn't know the difference.
    Used when strings should not be empty, and empty source data means unknown.
    """
    if s:
        return s
    return None

num_failures = 0

for record in csv.DictReader(sys.stdin):
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

    request = urllib2.Request(api_url, json.dumps({'supplier': supplier}), headers)
    try:
        urllib2.urlopen(request)
    except urllib2.HTTPError, e:
        num_failures += 1
        logging.error('Error adding supplier {}: server returned code {} {}'.format(supplier['code'], e.code, e.fp.read()))

if num_failures > 0:
    sys.exit(1)
