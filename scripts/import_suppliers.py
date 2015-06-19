#!/usr/bin/env python
"""Import SSP export files into the API

Usage:
        import_suppliers.py <endpoint> <access_token> <filename> [options]

    --cert=<cert>   Path to certificate file to verify against
    -v, --verbose   Enable verbose output for errors

Example:
    ./import_suppliers.py http://localhost:5000 myToken ~/myData/myData.json
"""
from __future__ import print_function
import sys
import json
import requests
from datetime import datetime

from docopt import docopt


def print_progress(counter, start_time):
    if counter % 100 == 0:
        time_delta = datetime.utcnow() - start_time
        print("{} in {} ({}/s)".format(counter,
                                       time_delta,
                                       counter / time_delta.total_seconds()))


class SupplierPutter(object):
    def __init__(self, endpoint, access_token, cert=None):
        self.endpoint = endpoint
        self.access_token = access_token
        self.cert = cert

    def import_supplier(self, supplier):

        data = {'suppliers': self.make_supplier_json(supplier)}
        supplier_id = data['suppliers']['id']
        url = '{0}/{1}'.format(self.endpoint, supplier_id)

        response = requests.put(
            url,
            data=json.dumps(data),
            headers={
                "content-type": "application/json",
                "authorization": "Bearer {}".format(self.access_token),
                },
            verify=self.cert if self.cert else True)

        return supplier_id, response

    @staticmethod
    def make_supplier_json(json_from_file):
        """
        FROM THIS >>

        {
            "supplierId": 92749,
            "name": "Central Technology Ltd",
            "description": "Daisy is the UK\u2019s largest independent",
            "website": "http://www.ct.co.uk",
            "contactName": "Richard Thompson",
            "contactEmail": "richard.thompson@ct.co.uk",
            "contactPhone": "0845 413 8888",
            "address": {
                "address1": "The Bridge Business Park",
                "address2": null,
                "city": "Chesterfield",
                "country": "United Kingdom",
                "postcode": "GU12 4RQ"
             },
            "dunsNumber": "733053339",
            "eSourcingId": null,
            "clientsString": "Home Office,Metropolitan Police,Aviva"
        }

        TO THIS >>

        {
          "id": 92749,
          "name": "Central Technology Ltd",
          "description": "Daisy is the UK\u2019s largest independent",
          "contactInformation": [
            {
              "website": "http://www.ct.co.uk",
              "contactName": "Richard Thompson",
              "email": "richard.thompson@ct.co.uk",
              "phoneNumber": "0845 413 8888",
              "address1": "The Bridge Business Park",
              "address2": null,
              "city": "Chesterfield",
              "country": "United Kingdom",
              "postcode": "GU12 4RQ"
            }
          ],
          "dunsNumber": "733053339",
          "eSourcingId": null,
          "clients":
          [
            "Home Office",
            "Metropolitan Police",
            "Aviva",
            "ITV",
          ]
        }
        """
        # variable either set to empty string or value of `clientsString` key
        clients_string = '' if 'clientsString' not in json_from_file.keys() \
            else json_from_file['clientsString']

        # `clientsString` list of (comma-separated) clients or empty
        json_from_file['clientsString'] = \
            SupplierPutter.split_comma_separated_value_string_into_list(
                clients_string
            )

        json_from_file = SupplierPutter.change_key_names(
            json_from_file,
            [
                ['clientsString', 'clients'],
                ['contactEmail', 'email'],
                ['contactPhone', 'phoneNumber'],
                ['supplierId', 'id']
            ]
        )

        # key/values nested behind `contactInformation` object
        json_from_file = SupplierPutter.nest_key_value_pairs(
            json_from_file,
            'contactInformation',
            ['email', 'website', 'phoneNumber', 'contactName', 'address']
        )

        # key/values in `address` un-nested (flush with `contactInformation`)
        json_from_file['contactInformation'] = \
            SupplierPutter.un_nest_key_value_pairs(
                json_from_file['contactInformation'],
                'address'
            )

        json_from_file['contactInformation'] = \
            SupplierPutter.convert_a_json_object_into_an_array_with_one_entry(
                json_from_file['contactInformation']
            )

        json_from_file = \
            SupplierPutter.convert_values_to_utf8_except_blacklisted_keys(
                json_from_file,
                ['id', 'clients', 'contactInformation']
            )

        return json_from_file

    @staticmethod
    def convert_values_to_utf8_except_blacklisted_keys(obj, blacklist):
        for key in obj.keys():
            if key not in blacklist:
                obj[key] = SupplierPutter.convert_string_to_utf8(obj[key])

        return obj

    @staticmethod
    def convert_string_to_utf8(string):
        # check if it's a string value
        if isinstance(string, str):
            return unicode(string, 'utf-8')

        else:
            return string

    @staticmethod
    def split_comma_separated_value_string_into_list(string):
        if not string:
            return []

        return [value for value in
                map(unicode.strip, string.split(',')) if len(value) is not 0]

    @staticmethod
    def un_nest_key_value_pairs(obj, key_of_nested_obj):
        if key_of_nested_obj not in obj.keys():
            return obj

        nested_obj = obj[key_of_nested_obj]

        obj = drop_foreign_fields(
            obj,
            [key_of_nested_obj]
        )

        for key in nested_obj.keys():
            obj[key] = nested_obj[key]

        return obj

    @staticmethod
    def nest_key_value_pairs(base_obj, key_for_new_obj, keys_to_nest):

        base_obj[key_for_new_obj] = {}

        for key_to_nest in keys_to_nest:
            if key_to_nest in base_obj.keys():
                # Maybe an else if the key isn't here.
                base_obj[key_for_new_obj][key_to_nest] = \
                    base_obj.pop(key_to_nest)

        return base_obj

    @staticmethod
    def change_key_names(obj, list_of_lists_of_key_pairs):

        for key_pair in list_of_lists_of_key_pairs:
            if len(key_pair) is 2:
                obj = SupplierPutter.change_key_name(
                    obj,
                    key_pair[0],
                    key_pair[1]
                )

        return obj

    @staticmethod
    def change_key_name(obj, old_key, new_key):
        if old_key in obj.keys():
            obj[new_key] = obj.pop(old_key)

        return obj

    @staticmethod
    def convert_a_json_object_into_an_array_with_one_entry(obj):

        temp = [{}]

        for key in obj.keys():
            temp[0][key] = obj.pop(key)

        obj = temp

        return obj


# this is copied + pasted from app/main/utils.py
def drop_foreign_fields(json_object, list_of_keys):
    json_object = json_object.copy()
    for key in list_of_keys:
        json_object.pop(key, None)

    return json_object


def do_import(base_url, access_token, filename, cert, verbose):
    endpoint = "{}/suppliers".format(base_url)
    print("Base URL: {}".format(base_url))
    print("Access token: {}".format(access_token))
    print("Filename: {}".format(filename))

    putter = SupplierPutter(endpoint, access_token, cert)

    counter = 0
    start_time = datetime.utcnow()

    with open(filename) as data_file:
        try:
            json_from_file = json.load(data_file)
        except ValueError:
            print("Skipping {}: not a valid JSON file".format(filename))

    for supplier in json_from_file['suppliers']:
        supplier_id, response = putter.import_supplier(supplier)

        if response is None:
            print("ERROR: Supplier (id={}) not imported".format(supplier_id),
                  file=sys.stderr)
        elif response.status_code / 100 != 2:
            print("ERROR: {} on Supplier (id={})".format(
                response.status_code,
                supplier_id
            ),
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
