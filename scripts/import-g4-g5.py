#!/usr/bin/env python
"""Process G5 JSON export file and import services into API

Usage:
    import-g4-g5.py <endpoint> <access_token> <g4_g5_export_file> [options]

    --cert=<cert>   Path to certificate file to verify against

Arguments:
    endpoint         The API endpoint to PUT services to
    access_token     Access token for the API
    g4_g5_export_file   The file to process

Example:
    ./import-g4-g5.py http://localhost:5000 myToken ~/myData.json
"""
from datetime import datetime
from docopt import docopt

import getpass
import itertools
import json
import requests


def print_progress(counter, start_time):
    if counter % 100 == 0:
        time_delta = datetime.utcnow() - start_time
        print("{} in {} ({}/s)".format(counter,
                                       time_delta,
                                       counter / time_delta.total_seconds()))


class ServicePutter(object):
    def __init__(self, endpoint, access_token, cert=None):
        self.endpoint = endpoint
        self.access_token = access_token
        self.cert = cert

    def __call__(self, service_json):
        try:
            service_id = str(service_json["id"])
        except ValueError:
            print("Skipping {}: could not get ID".format(service_json))
            return service_id, None
        data = {'update_details': {'updated_by': getpass.getuser()},
                'services': service_json}
        url = '{}/{}'.format(self.endpoint, data['services']['id'])
        response = requests.put(
            url,
            data=json.dumps(data),
            headers={
                "content-type": "application/json",
                "authorization": "Bearer {}".format(self.access_token),
                },
            verify=self.cert if self.cert else True)
        return service_id, response


def do_import(base_url, access_token, export_file, cert):
    endpoint = "{}/services".format(base_url)
    print("Base URL: {}".format(base_url))
    print("Access token: {}".format(access_token))
    print("Export file: {}".format(export_file))

    mapper = itertools.imap
    putter = ServicePutter(endpoint, access_token, cert)
    counter = 0
    start_time = datetime.utcnow()

    with open(export_file) as f:
        data = json.loads(f.read())

        for service_id, response in mapper(putter, data["services"]):
            if response is None:
                print("ERR: {} not imported".format(service_id))
            elif response.status_code / 100 != 2:
                print("ERR: {} on {}".format(response.status_code, service_id))
            else:
                counter += 1
                print_progress(counter, start_time)

        print_progress(counter, start_time)

if __name__ == "__main__":
    arguments = docopt(__doc__)
    do_import(
        base_url=arguments['<endpoint>'],
        access_token=arguments['<access_token>'],
        export_file=arguments['<g4_g5_export_file>'],
        cert=arguments['--cert']
        )
