#!/usr/bin/env python2
import csv
import json

from utils import makeClient, check_response


def run_import(input_file, client):
    num_successes = 0

    for record in csv.DictReader(input_file):

        price = {
            'supplier_name': record['supplier'],
            'service_name': record['service'],
            'region_name': record['region'],
            'price': float(record['price'])
        }

        check_response(
            client.post('/api/service-type-prices',
                        data=json.dumps({'price': price}),
                        content_type='application/json'))

        num_successes += 1
        print '{}:{},{},{},{}'.format(num_successes, price['supplier_name'],
                                      price['service_name'], price['region_name'], price['price'])

    print 'Total:{}'.format(num_successes)


if __name__ == '__main__':
    import sys
    client = makeClient()

    run_import(sys.stdin, client)
