from __future__ import absolute_import

import os
import json

from nose.tools import assert_equal, assert_false
from jsonschema import validate, SchemaError, ValidationError

from app.validation import validate_json


EXAMPLE_LISTING_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                    '..', 'example_listings'))


def test_all_schemas_are_valid():
    for file_name in os.listdir('json_schemas'):
        if os.path.isfile('json_schemas/%s' % file_name):
            print('Testing schema: %s' % file_name)
            with open('json_schemas/%s' % file_name) as json_schema_file:
                assert check_schema(json.load(json_schema_file))


def test_example_json_validates_correctly():
    check_example_listing("SSP-JSON-SCS", assert_equal, "G6-SCS")
    check_example_listing("SSP-JSON-SaaS", assert_equal, "G6-SaaS")
    check_example_listing("SSP-JSON-PaaS", assert_equal, "G6-PaaS")
    check_example_listing("SSP-JSON-IaaS", assert_equal, "G6-IaaS")
    check_example_listing("SSP-INVALID", assert_false)


def check_example_listing(name, assertion, *args):
    listing_path = os.path.join(EXAMPLE_LISTING_PATH, '{}.json'.format(name))
    with open(listing_path) as json_file:
        json_data = json.load(json_file)
        assertion(validate_json(json_data), *args)


def check_schema(schema):
    try:
        validate({}, schema)
    except SchemaError as ex:
        print('Invalid JSON schema: %s' % ex.message)
        return False
    except ValidationError:
        return True
    else:
        return True
