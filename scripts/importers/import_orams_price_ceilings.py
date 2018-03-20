#!/usr/bin/env python2
import csv
import json

from utils import makeClient, check_response


def run_import(input_file, client):
    num_successes = 0
    num_updates = 0

    for record in csv.DictReader(input_file):

        price = {
            'supplier_name': record['supplier'],
            'service_name': record['service'],
            'sub_service': record['sub_service'],
            'region_name': record['region'],
            'state': record['state'],
            'price': float(record['price_ceiling'])
        }

        response = client.post('/api/service-type-price-ceilings',
                               data=json.dumps({'price': price}),
                               content_type='application/json')
        data = check_response(response, False)
        msg = data.get('msg')
        updated = response.status_code == 201

        if updated is True:
            num_updates += 1

        num_successes += 1
        print ('{:>5}[msg={}]:{},{},{},{},{}'
               .format(num_successes,
                       msg,
                       price['supplier_name'],
                       price['service_name'],
                       price['region_name'],
                       price['state'],
                       price['price']))

    print 'Total:{}, Updates:{}'.format(num_successes, num_updates)


if __name__ == '__main__':
    import sys
    client = makeClient()

    run_import(sys.stdin, client)
