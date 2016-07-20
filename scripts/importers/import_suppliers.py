#!/usr/bin/env python2

#  Example usage:
#  ./scripts/importers/import_suppliers.py http://data-api.example.com/ < 'example_listings/test_source_data/DMP Data Source - Test data.csv'
import csv
import json
import os
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
    if s:
        return s
    return None

num_failures = 0

csv_input = csv.reader(sys.stdin)
csv_input.next()  # drop header
for record in csv_input:
    supplier = {
        'code': record[0],
        'name': record[1],
        'summary': record[2],
        'abn': record[3].strip(),
        'address': {
            'addressLine': nonEmptyOrNone(record[4]),
            'suburb': record[5],
            'state': record[6],
            'postalCode': record[7],
        },
        'contacts': [{
            'name': record[8],
            'role': nonEmptyOrNone(record[9]),
            'email': nonEmptyOrNone(record[10]),
            'phone': nonEmptyOrNone(record[11]),
            'fax': nonEmptyOrNone(record[12]),
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
