#!/usr/bin/env python2
import csv
import json

from utils import makeClient, check_response


def run_import(input_file, client):
    num_successes = 0

    for record in csv.DictReader(input_file):

        region = {
            'name': record['Region'],
        }

        json_data = check_response(
            client.post('/api/regions',
                        data=json.dumps({'region': region}),
                        content_type='application/json'))

        region_id = json_data['region']['id']

        location = {
            'name': record['Location'],
            'region_id': region_id,
            'state': record['State'],
            'postal_code': record['Postcode']
        }

        check_response(
            client.post(
                '/api/locations',
                data=json.dumps({'location': location}),
                content_type='application/json'))

        print '{},{}'.format(region['name'], location['name'])
        num_successes += 1

    print 'Total:{}'.format(num_successes)


if __name__ == '__main__':
    import sys
    client = makeClient()

    run_import(sys.stdin, client)
