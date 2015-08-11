#!/usr/bin/env python
"""Import SSP export files into the API

Usage:
    import_users.py <endpoint> <access_token> <filename> [options]

    --cert=<cert>   Path to certificate file to verify against
    -v, --verbose   Enable verbose output for errors

Example:
    ./import_users.py http://localhost:5000 myToken ~/myData.file.dat
"""
from __future__ import print_function
import sys
import json
import os
from datetime import datetime

import requests
from docopt import docopt


user_roles = {}


def list_files(directory):
    for root, subdirs, files in os.walk(directory):
        for filename in files:
            yield os.path.abspath(os.path.join(root, filename))

        for subdir in subdirs:
            for subfile in list_files(subdir):
                yield subfile


def print_progress(counter, start_time):
    if counter % 100 == 0:
        time_delta = datetime.utcnow() - start_time
        print("{} in {} ({}/s)".format(counter,
                                       time_delta,
                                       counter / time_delta.total_seconds()))


class UserPutter(object):
    def __init__(self, endpoint, access_token, cert=None):
        self.endpoint = endpoint
        self.access_token = access_token
        self.cert = cert

    def post_user(self, user):
        user = self.make_user_json(user)
        data = {'users': user}
        response = requests.post(
            self.endpoint,
            data=json.dumps(data),
            headers={
                "content-type": "application/json",
                "authorization": "Bearer {}".format(self.access_token),
            },
            verify=self.cert if self.cert else True)

        if response.status_code is not 201:
            print("failed: {}".format(user['emailAddress']))

        return user['emailAddress'], response

    @staticmethod
    def make_user_json(json_from_file):
        email = json_from_file['email'].lower()
        name = json_from_file['firstName'] + " " + json_from_file['lastName']

        if "ROLE_SUPPLIER" in json_from_file['roles']:
            role = "supplier"
        elif "ADMIN" in json_from_file['roles']:
            role = "admin"
        else:
            role = "buyer"

        user = {
            'hashpw': False,
            'name': name,
            'role': role,
            'emailAddress': email,
            'password': json_from_file['password']
        }

        if role == 'supplier':
            user['supplierId'] = json_from_file['supplierId']

        return user


def do_import(base_url, access_token, filename, cert, verbose):
    endpoint = "{}/users".format(base_url)
    print("Base URL: {}".format(base_url))
    print("Access token: {}".format(access_token))
    print("Filename: {}".format(filename))

    putter = UserPutter(endpoint, access_token, cert)

    counter = 0
    start_time = datetime.utcnow()

    with open(filename) as data_file:
        try:
            json_from_file = json.load(data_file)
        except ValueError:
            print("Skipping {}: not a valid JSON file".format(filename))

    for user in json_from_file['users']:
        email = user['email'].lower()

        role = "buyer"
        if "ROLE_SUPPLIER" in user['roles']:
            role = "supplier"

        temp = user_roles.get(email, None)

        if role == "supplier" or temp is None:
            user_roles[email] = {"role": role,
                                 "password": user['password']}

    for user in json_from_file['users']:
        username, response = putter.post_user(user)
        if response is None:
            print("ERROR: {} not imported".format(username),
                  file=sys.stderr)
        elif int(response.status_code / 100) != 2:
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
