from __future__ import absolute_import

import os
import json

from nose.tools import assert_equal, assert_false
from jsonschema import validate, SchemaError, ValidationError

from app.validation import validate_json, \
    validates_against_schema, UPDATER_SCHEMA


EXAMPLE_LISTING_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                    '..', 'example_listings'))


def test_all_schemas_are_valid():
    for file_name in os.listdir('json_schemas'):
        file_path = 'json_schemas/%s' % file_name
        if os.path.isfile(file_path):
            yield check_schema_file, file_path


def test_updater_json_validates_correctly():
    invalid_updater_no_reason = {'updated_by': 'this'}
    invalid_updater_no_username = {'update_reason': 'this'}
    invalid_updater_no_fields = {'invalid': 'this'}
    valid_updater = {'updated_by': 'this', 'update_reason': 'hi'}

    assert_equal(validates_against_schema(
        UPDATER_SCHEMA, invalid_updater_no_reason), False)
    assert_equal(validates_against_schema(
        UPDATER_SCHEMA, invalid_updater_no_username), False)
    assert_equal(validates_against_schema(
        UPDATER_SCHEMA, invalid_updater_no_fields), False)
    assert_equal(validates_against_schema(
        UPDATER_SCHEMA, valid_updater), True)


def test_example_json_validates_correctly():
    cases = [
        ("SSP-JSON-SCS", "G6-SCS"),
        ("SSP-JSON-SaaS", "G6-SaaS"),
        ("SSP-JSON-PaaS", "G6-PaaS"),
        ("SSP-JSON-IaaS", "G6-IaaS"),
        ("SSP-INVALID", False)
    ]

    for example, expected, in cases:
        data = load_example_listing(example)
        yield assert_example, example, validate_json(data), expected


def test_additional_fields_are_not_allowed():
    cases = [
        ("SSP-JSON-SCS", False),
        ("SSP-JSON-SaaS", False),
        ("SSP-JSON-PaaS", False),
        ("SSP-JSON-IaaS", False),
    ]

    for example, expected in cases:
        data = load_example_listing(example)
        data.update({'newKey': 1})
        yield assert_example, example, validate_json(data), expected


def assert_example(name, result, expected):
    assert_equal(result, expected)


def load_example_listing(name):
    listing_path = os.path.join(EXAMPLE_LISTING_PATH, '{}.json'.format(name))
    with open(listing_path) as json_file:
        json_data = json.load(json_file)

        return json_data


def check_schema_file(file_path):
    with open(file_path) as json_schema_file:
        assert check_schema(json.load(json_schema_file))


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
