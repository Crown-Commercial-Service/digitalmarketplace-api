#!/usr/bin/env python2
import csv
import json

from utils import makeClient, check_response


def run_import(input_file, client):
    num_successes = 0

    for record in csv.DictReader(input_file):

        service_type = {
            'category_name': record['Type'],
            'name': record['Service'],
            'framework_id': 9,
            'lot_id': 11
        }

        json_data = check_response(
            client.post('/api/service-types',
                        data=json.dumps({'service_type': service_type}),
                        content_type='application/json'))

        print '{},{}'.format(json_data['service_type']['category']['name'], json_data['service_type']['name'])
        num_successes += 1

    print 'Total:{}'.format(num_successes)


if __name__ == '__main__':
    import sys
    client = makeClient()

    run_import(sys.stdin, client)
