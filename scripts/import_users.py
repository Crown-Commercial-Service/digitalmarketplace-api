#!/usr/bin/env python
"""Import SSP export files into the API

Usage:
    import_users.py <endpoint> <access_token> <listing_dir> [options]

    --cert=<cert>   Path to certificate file to verify against
    --serial        Do not run in parallel (useful for debugging)
    -v, --verbose   Enable verbose output for errors

Example:
    ./import_users.py --serial http://localhost:5000 myToken ~/myData
"""
from __future__ import print_function
import sys
import json
import os
import getpass
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


class UserPutter(object):
    def __init__(self, endpoint, access_token, cert=None):
        self.endpoint = endpoint
        self.access_token = access_token
        self.cert = cert

    def __call__(self, file_path):
        with open(file_path) as f:
            try:
                json_from_file = json.load(f)
            except ValueError:
                print("Skipping {}: not a valid JSON file".format(file_path))
                return file_path, None

        for i in json_from_file['users']:
            data = {'users': self.make_user_json(i)}
            response = requests.post(
                self.endpoint,
                data=json.dumps(data),
                headers={
                    "content-type": "application/json",
                    "authorization": "Bearer {}".format(self.access_token),
                },
                verify=self.cert if self.cert else True)
            print(response)

        return file_path, 200

    @staticmethod
    def make_user_json(json_from_file):
        name = json_from_file['firstName'] + " " + json_from_file['lastName']
        return {
            'hashpw': False,
            'name': name,
            'email_address': json_from_file['email'],
            'password': json_from_file['password']
        }


def do_import(base_url, access_token, listing_dir, serial, cert, verbose):
    endpoint = "{}/users".format(base_url)
    print("Base URL: {}".format(base_url))
    print("Access token: {}".format(access_token))
    print("Listing dir: {}".format(listing_dir))

    if serial:
        mapper = itertools.imap
    else:
        pool = multiprocessing.Pool(10)
        mapper = pool.imap

    putter = UserPutter(endpoint, access_token, cert)

    counter = 0
    start_time = datetime.now()
    for file_path, response in mapper(putter, list_files(listing_dir)):
        if response is None:
            print("ERROR: {} not imported".format(file_path),
                  file=sys.stderr)
        elif response.status_code / 100 != 2:
            print("ERROR: {} on {}".format(response.status_code, file_path),
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
        listing_dir=arguments['<listing_dir>'],
        serial=arguments['--serial'],
        cert=arguments['--cert'],
        verbose=arguments['--verbose'],
    )
