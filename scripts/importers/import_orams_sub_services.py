#!/usr/bin/env python2
import csv
import json

from utils import makeClient, check_response


def run_import(input_file, client):
    num_successes = 0

    json_data = check_response(
        client.post('/api/service-sub-types',
                    data=json.dumps({'service_sub_type': {'name': ''}}),
                    content_type='application/json'))

    for record in csv.DictReader(input_file):

        service_sub_type = {
            'name': record['Name']
        }

        json_data = check_response(
            client.post('/api/service-sub-types',
                        data=json.dumps({'service_sub_type': service_sub_type}),
                        content_type='application/json'))

        print '{}'.format(json_data['service_sub_type']['name'])
        num_successes += 1

    print 'Total:{}'.format(num_successes)


if __name__ == '__main__':
    import sys
    client = makeClient()

    run_import(sys.stdin, client)
