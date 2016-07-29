#!/usr/bin/env python2

#  Example usage:
#  ./scripts/importers/import_prices.py http://data-api.example.com/ < 'example_listings/test_source_data/DMP Data Source - Test price data.csv'  # noqa
from collections import namedtuple
import csv
import json
import logging
import re
import sys
import urllib2

from dmutils.data_tools import ValidationError, parse_money
from utils import nonEmptyOrNone, makeClient


Role = namedtuple('Role', 'role category')


def getRoleTable(client):
    result = client.get('/roles')
    if result.status_code != 200:
        raise Exception('Failed to get roles. HTTP error {}: {}'.format(result.status_code, result.data))
    data = json.loads(result.data)
    roles = [Role(role=r['role'], category=r['category']) for r in data['roles']]
    table = {}
    for role in roles:
        if role.role in roles:
            raise Exception('Duplicate role name "{}".  More sophisticated role lookup may be required.')
        table[role.role.lower()] = role
    return table


def getSupplierCodeFromName(client, name):
    name = name.strip()
    path = '/suppliers?name={}'.format(urllib2.quote(name))
    result = client.get(path)
    if result.status_code >= 400:
        logging.error('Failed to find supplier "{}".  HTTP error {}: {}'.format(name, result.status_code, result.data))
        return None
    data = json.loads(result.data)
    suppliers = data['suppliers']
    if len(suppliers) != 1:
        logging.error('Error searching for supplier "{}": {} results found'.format(name, len(suppliers)))
        return None
    return suppliers[0]['code']


def filterDudPrice(price):
    """
    The source data sometimes has empty strings or $0.00 to represent 'no price given'.
    """
    if not price:
        return None
    value = parse_money(price)
    if value == 0:
        return None
    return price


def run_import(input_file, client):
    num_failures = 0
    num_successes = 0

    prices = {}
    name_to_code = {}

    roles = getRoleTable(client)

    for record in csv.DictReader(input_file):
        name = record['Name']
        if name in name_to_code:
            code = name_to_code[name]
        else:
            code = getSupplierCodeFromName(client, record['Name'])
            name_to_code[name] = code
            if code is not None:
                prices[code] = []

        if code is None:
            continue

        role = roles[record['Role'].lower()]
        prices[code].append({
            'serviceRole': {
                'role': role.role,
                'category': role.category,
            },
            'hourlyRate': filterDudPrice(record['hourly rate']),
            'dailyRate': filterDudPrice(record['daily rate']),
            'gstIncluded': True,
        })

    for code, price_schedule in prices.items():
        supplier_update = {'prices': price_schedule}
        data = json.dumps({'supplier': supplier_update})
        result = client.patch('/suppliers/{}'.format(code), data=data, content_type='application/json')
        if result.status_code == 200:
            num_successes += 1
        else:
            num_failures += 1
            logging.error('Failed to update prices for supplier {}.  HTTP error {}: {}'.format(code,
                                                                                               result.status_code,
                                                                                               result.data))

    return num_failures, num_successes


if __name__ == '__main__':
    client = makeClient()

    num_failures, num_successes = run_import(sys.stdin, client)
    if num_failures > 0:
        sys.exit(1)
