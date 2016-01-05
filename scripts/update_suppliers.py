#!/usr/bin/env python
"""
Update a series of suppliers from a file of JSON objects, one per line.

The JSON objects should have an "id" field in them with the supplier ID
so that the update URL can be generated. The rest of the object should
be what needs to be updated.

{"id": 1234, "name": "Foo Bar"}

Usage:
    update-suppliers.py <data_api_endpoint> <data_api_token> <updates_path> <updated_by>
"""
from docopt import docopt
from dmapiclient import DataAPIClient

import json


def load_updates(updates_path):
    with open(updates_path) as f:
        for line in f:
            yield json.loads(line)


def update_suppliers(data_api_endpoint, data_api_token, updates_path, updated_by):
    client = DataAPIClient(data_api_endpoint, data_api_token)

    for update in load_updates(updates_path):
        print("Updating {}".format(update))
        client.update_supplier(
            update.pop('id'),
            update,
            updated_by)


if __name__ == '__main__':
    arguments = docopt(__doc__)
    update_suppliers(
        data_api_endpoint=arguments['<data_api_endpoint>'],
        data_api_token=arguments['<data_api_token>'],
        updates_path=arguments['<updates_path>'],
        updated_by=arguments['<updated_by>'])
