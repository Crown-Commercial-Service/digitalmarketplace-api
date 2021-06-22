#!/usr/bin/env python
"""Read suppliers from the API endpoint and write to target API.

Usage:
    index_suppliers_from_api.py <api_endpoint> <api_access_token>
                                <source_api_endpoint> <source_api_access_token>
                                [options]

    --serial        Do not run in parallel (useful for debugging)
    --users=<PASS>  Create user accounts for each supplier and set the
                    passwords to PASS

Example:
    ./import_suppliers_from_api.py http://api myToken http://source-api token
"""

from six.moves import map

import sys
import multiprocessing
from itertools import islice
from datetime import datetime

from docopt import docopt

import dmapiclient


CLEAN_FIELDS = {
    'email': 'supplier-{}@user.dmdev',
    'phoneNumber': '00000{}'

}


def request_suppliers(api_url, api_access_token, page=1):

    data_client = dmapiclient.DataAPIClient(
        api_url,
        api_access_token
    )

    while page:
        suppliers_page = data_client.find_suppliers(page=page)

        for supplier in suppliers_page['suppliers']:
            yield supplier

        if suppliers_page['links'].get('next'):
            page += 1
        else:
            return


def print_progress(counter, start_time):
    if counter % 100 == 0:
        time_delta = datetime.utcnow() - start_time
        print("{} in {} ({}/s)".format(counter,
                                       time_delta,
                                       counter / time_delta.total_seconds()))


class SupplierUpdater(object):
    def __init__(self, endpoint, access_token, user_password=None):
        self.endpoint = endpoint
        self.access_token = access_token
        self.user_password = user_password

    def __call__(self, supplier):
        client = dmapiclient.DataAPIClient(self.endpoint, self.access_token)
        try:
            client.import_supplier(supplier['id'],
                                   self.clean_data(supplier, supplier['id']))
        except dmapiclient.APIError as e:
            print("ERROR: {}. {} not imported".format(str(e),
                                                      supplier.get('id')),
                  file=sys.stderr)
            return False

        if not self.user_password:
            return True

        try:
            client.create_user({
                'role': 'supplier',
                'emailAddress': CLEAN_FIELDS['email'].format(
                    supplier['id']
                ),
                'password': self.user_password,
                'name': supplier['name'],
                'supplierId': supplier['id'],
            })
        except dmapiclient.APIError as e:
            if e.status_code != 409:
                print("ERROR: {}. Could not create user account for {}".format(
                    str(e), supplier.get('id')), file=sys.stderr)
                return False

        return True

    def clean_data(self, supplier, *format_data):
        for field in supplier:
            if field in CLEAN_FIELDS:
                supplier[field] = CLEAN_FIELDS[field].format(*format_data)
            elif isinstance(supplier[field], dict):
                supplier[field] = self.clean_data(supplier[field].copy(),
                                                  *format_data)
            elif isinstance(supplier[field], list):
                supplier[field] = [
                    self.clean_data(item.copy(), *format_data)
                    if isinstance(item, dict) else item
                    for item in supplier[field]
                ]
        return supplier


def do_index(api_url, api_access_token, source_api_url,
             source_api_access_token, serial, users):
    print("Data API URL: {}".format(api_url))
    print("Source Data API URL: {}".format(source_api_url))

    if serial:
        pool = None
        mapper = map
    else:
        pool = multiprocessing.Pool(10)
        mapper = pool.imap

    indexer = SupplierUpdater(api_url, api_access_token, user_password=users)

    counter = 0
    start_time = datetime.utcnow()
    status = True

    iter_suppliers = request_suppliers(source_api_url, source_api_access_token)
    suppliers = True
    while suppliers:
        try:
            suppliers = list(islice(iter_suppliers, 0, 100))
        except dmapiclient.APIError as e:
            print('API request failed: {}'.format(str(e)), file=sys.stderr)
            return False

        for result in mapper(indexer, suppliers):
            counter += 1
            status = status and result
            print_progress(counter, start_time)

    return status

    print_progress(counter, start_time)

if __name__ == "__main__":
    arguments = docopt(__doc__)
    ok = do_index(
        api_url=arguments['<api_endpoint>'],
        api_access_token=arguments['<api_access_token>'],
        source_api_url=arguments['<source_api_endpoint>'],
        source_api_access_token=arguments['<source_api_access_token>'],
        serial=arguments['--serial'],
        users=arguments['--users'],
    )

    if not ok:
        sys.exit(1)
