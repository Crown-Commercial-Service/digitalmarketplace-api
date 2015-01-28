#!/usr/bin/env python
"""Import SSP export files into the API

Usage:
    import.py <endpoint> <access_token> <listing_dir> [--cert=<cert>] \
[--serial]

Options:
    --cert=<cert>   Path to certificate file to verify against
    --serial        Do not run in parallel (useful for debugging)

Example:
    ./import.py --serial http://localhost:5000 myToken ~/myData
"""
from __future__ import print_function
import sys
import json
import os
import itertools
import multiprocessing
from datetime import datetime

import requests
from docopt import docopt


def list_files(directory):
    for root, subdirs, files in os.walk(directory):
        for filename in files:
            yield os.path.abspath(os.path.join(root, filename))

        for subdir in subdirs:
            for subfile in list_files(subdir):
                yield subfile


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

    def __call__(self, file_path):
        with open(file_path) as f:
            data = json.load(f)
            data = {'services': data}
            url = '{}/{}'.format(self.endpoint, data['services']['id'])
            response = requests.put(
                url,
                data=json.dumps(data),
                headers={
                    "content-type": "application/json",
                    "authorization": "Bearer {}".format(self.access_token),
                },
                verify=self.cert if self.cert else True)
            return file_path, response


def do_import(base_url, access_token, listing_dir, serial, cert):
    endpoint = "{}/services".format(base_url)
    print("Base URL: {}".format(base_url))
    print("Access token: {}".format(access_token))
    print("Listing dir: {}".format(listing_dir))

    if serial:
        mapper = itertools.imap
    else:
        pool = multiprocessing.Pool(10)
        mapper = pool.imap

    putter = ServicePutter(endpoint, access_token, cert)

    counter = 0
    start_time = datetime.now()
    for file_path, response in mapper(putter, list_files(listing_dir)):
        if response.status_code / 100 != 2:
            print("ERROR: {} on {}".format(response.status_code, file_path),
                  file=sys.stderr)
        else:
            counter += 1
            print_progress(counter, start_time)

    print_progress(counter, start_time)

if __name__ == "__main__":
    arguments = docopt(__doc__)
    do_import(
        base_url=arguments['<endpoint>'],
        access_token=arguments['<access_token>'],
        listing_dir=arguments['<listing_dir>'],
        serial=arguments['--serial'],
        cert=arguments['--cert'])
