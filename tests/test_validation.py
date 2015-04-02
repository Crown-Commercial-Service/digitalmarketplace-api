from __future__ import absolute_import

import os
import json

from nose.tools import assert_equal
from jsonschema import validate, SchemaError, ValidationError

from app.validation import validate_json, detect_framework, \
    validates_against_schema, UPDATER_VALIDATOR, is_valid_service_id, \
    USERS_VALIDATOR, AUTH_USERS_VALIDATOR


EXAMPLE_LISTING_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                    '..', 'example_listings'))


def test_for_valid_service_id():
    cases = [
        ("valid-service-id", True),
        ("5-g5-0379-325", True),
        ("1234567890123456", True),
        ("VALID-service-id", True),
        ("invalid.service.id", False),
        ("invalid*service-id", False),
        ("", False),
        ("0123456789", True),
        ("012345678", False),
        ("01234567890123456789", True),
        ("012345678901234567890", False)
    ]

    for example, expected in cases:
        yield assert_equal, is_valid_service_id(example), expected, example


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
        UPDATER_VALIDATOR, invalid_updater_no_reason), False)
    assert_equal(validates_against_schema(
        UPDATER_VALIDATOR, invalid_updater_no_username), False)
    assert_equal(validates_against_schema(
        UPDATER_VALIDATOR, invalid_updater_no_fields), False)
    assert_equal(validates_against_schema(
        UPDATER_VALIDATOR, valid_updater), True)


def test_user_creation_validates():
    longer_than_255 = "a" * 256
    exactly_255 = "a" * 255
    case = [
        ({'email_address': 'this@that.com',
          'name': exactly_255,
          'password': exactly_255}, True, "valid"),
        ({'email_address': 'thisthat.com',
          'name': exactly_255,
          'password': exactly_255}, False, "invalid email thisthat.com"),
        ({'email_address': 'this@that',
          'name': exactly_255,
          'password': exactly_255}, False, "invalid email this@that"),
        ({'email_address': 'this@t@hat.com',
          'name': exactly_255,
          'password': exactly_255}, False, "invalid email this@t@hat.com"),
        ({'email_address': '',
          'name': exactly_255,
          'password': exactly_255}, False, "Missing email"),
        ({'email_address': 'this@that.com',
          'password': exactly_255}, False, "missing name"),
        ({'email_address': 'this@that.com',
          'name': exactly_255}, False, "missing password"),
        ({'email_address': 'this@that.com',
          'name': exactly_255,
          'password': longer_than_255}, False, "too long password"),
        ({'email_address': 'this@that.com',
          'name': exactly_255,
          'password': longer_than_255}, False, "too short password"),
        ({'email_address': 'this@that.com',
          'name': exactly_255,
          'password': ''}, False, "too short password"),
        ({'email_address': 'this@that.com',
          'name': '',
          'password': exactly_255}, False, "too short name"),
        ({'email_address': 'this@that.com',
          'name': exactly_255,
          'password': exactly_255,
          'hashpw': True}, True, "valid with hashpw"),
        ({'email_address': 'this@that.com',
          'name': exactly_255,
          'password': exactly_255,
          'hashpw': False}, True, "valid with dont hashpw"),
        ({'email_address': 'this@that.com',
          'name': exactly_255,
          'password': exactly_255,
          'hashpw': 'dewdew'}, False, "invalid hashpw")
    ]

    for example, expected, message in case:
        result = validates_against_schema(USERS_VALIDATOR, example)
        yield assert_equal, result, expected, message


def test_auth_user_validates():
    longer_than_255 = "a" * 256
    exactly_255 = "a" * 255
    case = [
        ({'email_address': 'this@that.com',
          'password': exactly_255}, True, "valid"),
        ({'email_address': 'thisthat.com',
          'password': exactly_255}, False, "invalid email thisthat.com"),
        ({'email_address': 'this@that',
          'password': exactly_255}, False, "invalid email this@that"),
        ({'email_address': 'this@t@hat.com',
          'password': exactly_255}, False, "invalid email this@t@hat.com"),
        ({'email_address': '',
          'password': exactly_255}, False, "Missing email"),
        ({'email_address': 'this@that.com',
          'name': exactly_255}, False, "missing password"),
        ({'email_address': 'this@that.com',
          'password': longer_than_255}, False, "too long password"),
        ({'email_address': 'this@that.com',
          'password': longer_than_255}, False, "too short password"),
        ({'email_address': 'this@that.com',
          'password': ''}, False, "too short password")
    ]

    for example, expected, message in case:
        result = validates_against_schema(AUTH_USERS_VALIDATOR, example)
        yield assert_equal, result, expected, message


def test_example_json_validates_correctly():
    cases = [
        ("G4", "G-Cloud 4"),
        ("G5", "G-Cloud 5"),
        ("G6-SCS", "G-Cloud 6"),
        ("G6-SaaS", "G-Cloud 6"),
        ("G6-PaaS", "G-Cloud 6"),
        ("G6-IaaS", "G-Cloud 6"),
        ("G6-INVALID", False)
    ]

    for example, expected, in cases:
        data = load_example_listing(example)
        yield assert_example, example, detect_framework(data), expected


def test_additional_fields_are_not_allowed():
    cases = [
        ("G4", False),
        ("G5", False),
        ("G6-SCS", False),
        ("G6-SaaS", False),
        ("G6-PaaS", False),
        ("G6-IaaS", False)
    ]

    for example, expected in cases:
        data = load_example_listing(example)
        data.update({'newKey': 1})
        yield assert_example, example, detect_framework(data), expected


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
