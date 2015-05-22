#!/usr/bin/env python
"""Read services from the API endpoint and write to search-api for indexing.

Usage:
    index_services.py <search_endpoint> <search_access_token> <api_endpoint>
              <api_access_token> [options]

    --serial        Do not run in parallel (useful for debugging)

Example:
    ./index_services.py http://search-api myToken http://data-api token
"""

from __future__ import print_function
from six.moves import map
import sys
import multiprocessing
from datetime import datetime

from docopt import docopt
from dmutils import apiclient


def request_services(api_url, api_access_token, page=1):

    data_client = apiclient.DataAPIClient(
        api_url,
        api_access_token
    )

    while page:
        try:
            services_page = data_client.find_services(page=page)
        except apiclient.APIError as e:
            print('API request failed: {}'.format(e.message), file=sys.stderr)
            return

        for service in services_page['services']:
            yield service

        if list(filter(lambda l: l == 'next', services_page['links'])):
            page += 1
        else:
            break


def print_progress(counter, start_time):
    if counter % 100 == 0:
        time_delta = datetime.now() - start_time
        print("{} in {} ({}/s)".format(counter,
                                       time_delta,
                                       counter / time_delta.total_seconds()))


class ServiceIndexer(object):
    def __init__(self, endpoint, access_token):
        self.endpoint = endpoint
        self.access_token = access_token

    def __call__(self, service):
        client = apiclient.SearchAPIClient(self.endpoint, self.access_token)
        try:
            if service['status'] == 'published':
                client.index(
                    service['id'],
                    service,
                    service['supplierName'],
                    service['frameworkName'])
            else:
                client.delete(service['id'])
        except apiclient.APIError as e:
            print("ERROR: {}. {} not indexed".format(e.message,
                                                     service.get('id')),
                  file=sys.stderr)


def do_index(search_api_url, search_api_access_token, data_api_url,
             data_api_access_token, serial):
    print("Search API URL: {}".format(search_api_url))
    print("Data API URL: {}".format(data_api_url))

    if serial:
        mapper = map
    else:
        pool = multiprocessing.Pool(10)
        mapper = pool.imap

    indexer = ServiceIndexer(search_api_url, search_api_access_token)

    counter = 0
    start_time = datetime.now()
    for _ in mapper(indexer, request_services(data_api_url,
                                              data_api_access_token)):
        counter += 1
        print_progress(counter, start_time)

    print_progress(counter, start_time)

if __name__ == "__main__":
    arguments = docopt(__doc__)
    do_index(
        search_api_url=arguments['<search_endpoint>'],
        search_api_access_token=arguments['<search_access_token>'],
        data_api_url=arguments['<api_endpoint>'],
        data_api_access_token=arguments['<api_access_token>'],
        serial=arguments['--serial'],
    )
