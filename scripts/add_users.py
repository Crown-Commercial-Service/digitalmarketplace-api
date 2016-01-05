#!/usr/bin/env python
"""
Add a series of users from a file of JSON objects, one per line.

The JSON user object lines can have the following fields:

{"name": "A. Non", "password": "pass12345", "emailAddress": "email@email.com", "role": "supplier", "supplierId": 12345}

Usage:
    add-users.py <data_api_endpoint> <data_api_token> <users_path>
"""
from docopt import docopt
from dmapiclient import DataAPIClient

import json


def load_users(users_path):
    with open(users_path) as f:
        for line in f:
            yield json.loads(line)


def update_suppliers(data_api_endpoint, data_api_token, users_path):
    client = DataAPIClient(data_api_endpoint, data_api_token)

    for user in load_users(users_path):
        print("Adding {}".format(user))
        client.create_user(user)


if __name__ == '__main__':
    arguments = docopt(__doc__)
    update_suppliers(
        data_api_endpoint=arguments['<data_api_endpoint>'],
        data_api_token=arguments['<data_api_token>'],
        users_path=arguments['<users_path>'])
