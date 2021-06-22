#!/usr/bin/env python
"""Read services from the API endpoint and write to target API.

Usage:
    import_services_from_api.py <api_endpoint> <api_access_token>
                                <source_api_endpoint> <source_api_access_token>
                                [options]

    --serial        Do not run in parallel (useful for debugging)

Example:
    ./import_services_from_api.py http://api myToken http://source-api token
"""

from six.moves import map

import getpass
import sys
import multiprocessing
from itertools import islice
from datetime import datetime

from docopt import docopt

import dmapiclient


CLEAN_FIELDS = {}


def request_services(api_url, api_access_token, page=1):

    data_client = dmapiclient.DataAPIClient(
        api_url,
        api_access_token
    )

    while page:
        services_page = data_client.find_services(page=page)

        for service in services_page['services']:
            yield service

        if 'links' in services_page:
            links = services_page['links']

            if isinstance(links, list):
                found = False
                for link in links:
                    if 'rel' in link:
                        if link['rel'] == 'next':
                            page += 1
                            found = True

                if not found:
                    return

            else:
                if 'next' in links:
                    page += 1
                else:
                    return
        else:
            return


def print_progress(counter, start_time):
    if counter % 100 == 0:
        time_delta = datetime.utcnow() - start_time
        print("{} in {} ({}/s)".format(counter,
                                       time_delta,
                                       counter / time_delta.total_seconds()))


class ServiceUpdater(object):
    def __init__(self, endpoint, access_token):
        self.endpoint = endpoint
        self.access_token = access_token

    def __call__(self, service):
        client = dmapiclient.DataAPIClient(self.endpoint, self.access_token)

        user = self.get_user(service)
        fix_data = self.update_data(service)
        cleaned_data = self.clean_data(fix_data)

        try:
            client.import_service(
                service['id'],
                cleaned_data,
                user
            )
            return True
        except dmapiclient.APIError as e:
            print("ERROR: {}. {} not imported".format(str(e),
                                                      service.get('id')),
                  file=sys.stderr)
            return False

    def get_user(self, service):
        if 'lastCompletedByEmail' in service:
            return service['lastCompletedByEmail']
        return getpass.getuser()

    def update_data(self, service):
        if 'lastCompleted' in service:
            service['createdAt'] = service['lastCompleted']
        service.pop('lastCompletedByEmail', None)
        service.pop('lastCompleted', None)
        service.pop('lastUpdated', None)
        service.pop('lastUpdatedByEmail', None)
        return service

    def clean_data(self, service):
        for field in CLEAN_FIELDS:
            if field in service:
                service[field] = CLEAN_FIELDS[field]
        return service


def do_index(api_url, api_access_token, source_api_url,
             source_api_access_token, serial):
    print("Data API URL: {}".format(api_url))
    print("Source Data API URL: {}".format(source_api_url))

    if serial:
        pool = None
        mapper = map
    else:
        pool = multiprocessing.Pool(10)
        mapper = pool.imap

    indexer = ServiceUpdater(api_url, api_access_token)

    counter = 0
    start_time = datetime.utcnow()
    status = True

    iter_services = request_services(source_api_url, source_api_access_token)
    services = True
    while services:
        try:
            services = list(islice(iter_services, 0, 100))
        except dmapiclient.APIError as e:
            print('API request failed: {}'.format(str(e)), file=sys.stderr)
            return False

        for result in mapper(indexer, services):
            counter += 1
            status = status and result
            print_progress(counter, start_time)

    print_progress(counter, start_time)
    return status


if __name__ == "__main__":
    arguments = docopt(__doc__)
    ok = do_index(
        api_url=arguments['<api_endpoint>'],
        api_access_token=arguments['<api_access_token>'],
        source_api_url=arguments['<source_api_endpoint>'],
        source_api_access_token=arguments['<source_api_access_token>'],
        serial=arguments['--serial'],
    )

    if not ok:
        sys.exit(1)
