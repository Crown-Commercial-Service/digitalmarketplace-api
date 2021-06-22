#!/usr/bin/env python
"""Update a service

Usage:
        update_service.py <endpoint> <access_token> <service_id> <filename>

Example:
    ./update_service.py http://localhost:5000 myToken ~/update.json
"""

import json
import requests
import getpass

from docopt import docopt


def update(base_url, access_token, filename, service_id):
    print(base_url)
    print(access_token)
    print(filename)
    print(service_id)

    endpoint = "{}/services/{}".format(base_url, service_id)

    with open(filename) as data_file:
        json_from_file = json.load(data_file)

        data = {
            'update_details': {
                'updated_by': getpass.getuser()
            },
            'services': json_from_file
        }

        print(endpoint)

        response = requests.post(
            endpoint,
            data=json.dumps(data),
            headers={
                "content-type": "application/json",
                "authorization": "Bearer {}".format(access_token),
                }
        )
        print(response.status_code)
        print(response.text)
        return service_id, response

if __name__ == "__main__":
    arguments = docopt(__doc__)
    update(
        base_url=arguments['<endpoint>'],
        access_token=arguments['<access_token>'],
        service_id=arguments['<service_id>'],
        filename=arguments['<filename>'],
    )
