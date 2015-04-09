#!/usr/bin/env python
"""Import SSP export files into the API

Usage:
    import_users.py <endpoint> <access_token> <filename> [options]

    --cert=<cert>   Path to certificate file to verify against
    -v, --verbose   Enable verbose output for errors

Example:
    ./import_users.py --serial http://localhost:5000 myToken ~/myData.file.dat
"""
from __future__ import print_function
import sys
import json
import os
from datetime import datetime

import requests
from docopt import docopt


roles = {}


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

    def post_user(self, user):
        for role in user['roles']:
            if role in roles:
                user[role] += 1
            else:
                user[role] = 1

        user = self.make_user_json(user)
        data = {'users': user}
        print("sending {}".format(user['email_address']))
        response = requests.post(
            self.endpoint,
            data=json.dumps(data),
            headers={
                "content-type": "application/json",
                "authorization": "Bearer {}".format(self.access_token),
            },
            verify=self.cert if self.cert else True)

        if response.status_code is not 200:
            print("failed: {}".format(user['email_address']))

        return user['email_address'], response

    @staticmethod
    def make_user_json(json_from_file):
        name = json_from_file['firstName'] + " " + json_from_file['lastName']
        if "ROLE_SUPPLIER" in json_from_file['roles']:
            role = "supplier"
        else:
            role = "buyer"

        return {
            'hashpw': False,
            'name': name,
            'role': role,
            'email_address': json_from_file['email'],
            'password': json_from_file['password']
        }


def do_import(base_url, access_token, filename, cert, verbose):
    endpoint = "{}/users".format(base_url)
    print("Base URL: {}".format(base_url))
    print("Access token: {}".format(access_token))
    print("Filename: {}".format(filename))

    putter = UserPutter(endpoint, access_token, cert)

    counter = 0
    start_time = datetime.now()

    data_file = open(filename)
    try:
        json_from_file = json.load(data_file)
    except ValueError:
        print("Skipping {}: not a valid JSON file".format(filename))

    for user in json_from_file['users']:
        username, response = putter.post_user(user)
        if response is None:
            print("ERROR: {} not imported".format(username),
                  file=sys.stderr)
        elif response.status_code / 100 != 2:
            print("ERROR: {} on {}".format(response.status_code, username),
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
        filename=arguments['<filename>'],
        cert=arguments['--cert'],
        verbose=arguments['--verbose'],
    )