#!/usr/bin/env python
"""Import services from source API endpoint

Usage:
    import.py <endpoint> <access_token> <source_api_endpoint>
              <source_api_access_token> [options]

    --cert=<cert>   Path to certificate file to verify against
    --serial        Do not run in parallel (useful for debugging)
    -v, --verbose   Enable verbose output for errors

Example:
    ./import.py --serial http://localhost:5000 myToken http://source-api token
"""
from __future__ import print_function
from six.moves import map
import sys
import json
import getpass
import multiprocessing
from datetime import datetime

import requests
from docopt import docopt


def request_services(api_url, api_access_token, page=1):
    page_url = '{}/services?page={}'.format(api_url, page)

    while page_url:
        services_page = requests.get(
            page_url,
            headers={
                'Authorization': 'Bearer {}'.format(api_access_token),
            }
        ).json()

        for service in services_page['services']:
            yield service

        page_url = list(
            filter(lambda l: l == 'next', services_page['links']))
        if page_url:
            page_url = page_url[0]['href']


def print_progress(counter, start_time):
    if counter % 100 == 0:
        time_delta = datetime.now() - start_time
        print("{} in {} ({}/s)".format(counter,
                                       time_delta,
                                       counter / time_delta.total_seconds()))


class ServicePutter(object):
    def __init__(self, endpoint, access_token, cert=None):
        self.endpoint = endpoint
        self.access_token = access_token
        self.cert = cert

    def __call__(self, data):
        data = {'update_details': {'updated_by': getpass.getuser(),
                                   'update_reason': 'service import'},
                'services': data}
        url = '{}/{}'.format(self.endpoint, data['services']['id'])
        response = requests.put(
            url,
            data=json.dumps(data),
            headers={
                "content-type": "application/json",
                "authorization": "Bearer {}".format(self.access_token),
            },
            verify=self.cert if self.cert else True)
        return data, response


def do_import(base_url, access_token, source_api_base_url,
              source_api_access_token, serial, cert, verbose):
    endpoint = "{}/services".format(base_url)
    print("Base URL: {}".format(base_url))
    print("Access token: {}".format(access_token))
    print("Source API: {}".format(source_api_base_url))

    if serial:
        mapper = map
    else:
        pool = multiprocessing.Pool(10)
        mapper = pool.imap

    putter = ServicePutter(endpoint, access_token, cert)

    counter = 0
    start_time = datetime.now()
    for service, response in mapper(putter,
                                    request_services(source_api_base_url,
                                                     source_api_access_token)):
        if response is None:
            print("ERROR: {} not imported".format(service.get('id')),
                  file=sys.stderr)
        elif int(response.status_code / 100) != 2:
            print("ERROR: {} on {}".format(response.status_code,
                                           service.get('id')),
                  file=sys.stderr)
            if verbose:
                print(response.text, file=sys.stderr)
        else:
            counter += 1
            print_progress(counter, start_time)

    print_progress(counter, start_time)

if __name__ == "__main__":
    arguments = docopt(__doc__)
    do_import(
        base_url=arguments['<endpoint>'],
        access_token=arguments['<access_token>'],
        source_api_base_url=arguments['<source_api_endpoint>'],
        source_api_access_token=arguments['<source_api_access_token>'],
        serial=arguments['--serial'],
        cert=arguments['--cert'],
        verbose=arguments['--verbose'],
    )
