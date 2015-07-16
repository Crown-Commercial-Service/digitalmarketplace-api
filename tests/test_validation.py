from __future__ import absolute_import

import os
import json

from nose.tools import assert_equal
from jsonschema import validate, SchemaError, ValidationError

from app.validation import detect_framework, \
    validates_against_schema, is_valid_service_id, \
    is_valid_date, is_valid_acknowledged_state, get_validation_errors, \
    is_valid_string

EXAMPLE_LISTING_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                    '..', 'example_listings'))


def test_for_valid_date():
    cases = [
        ("2010-01-01", True),
        ("2010-02-29", False),
        ("invalid", False)
    ]

    for example, expected in cases:
        yield assert_equal, is_valid_date(example), expected, example


def test_for_valid_acknowledged_state():
    cases = [
        ("all", True),
        ("true", True),
        ("false", True),
        ("2010-02-29", False),
        ("invalid", False)
    ]

    for example, expected in cases:
        yield assert_equal, is_valid_acknowledged_state(example), expected


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


def test_for_valid_string():
    cases = [
        ("valid-string", 1, 200, True),
        ("tooshort", 100, 200, False),
        ("toolong", 1, 1, False),
        ("1234567890123456", 1, 200, True),
        ("THIS-IS-VALID-id", 1, 200, True),
        ("invalid%chars&here", 1, 200, False),
        ("no spaces", 1, 200, False),
        ("no\nnewlines", 1, 200, False),
        ("123-and-strings", 1, 200, True),
    ]

    for example, min, max, expected in cases:
        yield assert_equal, is_valid_string(
            example, min, max), expected, example


def test_all_schemas_are_valid():
    for file_name in os.listdir('json_schemas'):
        file_path = 'json_schemas/%s' % file_name
        if os.path.isfile(file_path) and file_path.endswith(".json"):
            yield check_schema_file, file_path


def test_updater_json_validates_correctly():
    """
    This schema currently allows extra fields as part of a 2 stage
    migration of API validatiopn rules. This test will change back to
    not allowing the invalid fields when the utils is updated.
    :return:
    """
    invalid_updater_no_fields = {}
    invalid_updater_extra_fields = {'updated_by': 'this', 'invalid': 'this'}
    invalid_updater_only_invalid_fields = {'invalid': 'this'}
    valid_updater = {'updated_by': 'this'}

    assert_equal(validates_against_schema(
        'services-update', invalid_updater_no_fields), False)
    assert_equal(validates_against_schema(
        'services-update', invalid_updater_extra_fields), True)
    assert_equal(validates_against_schema(
        'services-update', invalid_updater_only_invalid_fields), False)
    assert_equal(validates_against_schema(
        'services-update', valid_updater), True)


def test_user_creation_validates():
    longer_than_255 = "a" * 256
    exactly_255 = "a" * 255
    case = [
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': exactly_255,
          'password': exactly_255}, True, "valid"),
        ({'emailAddress': 'thisthat.com',
          'role': 'buyer',
          'name': exactly_255,
          'password': exactly_255}, False, "invalid email thisthat.com"),
        ({'emailAddress': 'this@that',
          'role': 'buyer',
          'name': exactly_255,
          'password': exactly_255}, False, "invalid email this@that"),
        ({'emailAddress': 'this@t@hat.com',
          'role': 'buyer',
          'name': exactly_255,
          'password': exactly_255}, False, "invalid email this@t@hat.com"),
        ({'emailAddress': '',
          'role': 'buyer',
          'name': exactly_255,
          'password': exactly_255}, False, "Missing email"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'password': exactly_255}, False, "missing name"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': exactly_255}, False, "missing password"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': exactly_255,
          'password': longer_than_255}, False, "too long password"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': exactly_255,
          'password': longer_than_255}, False, "too short password"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': exactly_255,
          'password': ''}, False, "too short password"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': '',
          'password': exactly_255}, False, "too short name"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': exactly_255,
          'password': exactly_255,
          'hashpw': True}, True, "valid with hashpw"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': exactly_255,
          'password': exactly_255,
          'hashpw': False}, True, "valid with dont hashpw"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': exactly_255,
          'password': exactly_255,
          'hashpw': 'dewdew'}, False, "invalid hashpw"),
        ({'emailAddress': 'this@that.com',
          'role': 'invalid',
          'name': exactly_255,
          'password': exactly_255}, False, "invalid role"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': exactly_255,
          'supplierId': 123,
          'password': exactly_255}, True, "valid supplier id"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': exactly_255,
          'supplierId': '',
          'password': exactly_255}, False, "invalid supplier id (to short)"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': exactly_255,
          'supplierId': longer_than_255,
          'password': exactly_255}, False, "invalid supplier id (to long)")
    ]

    for example, expected, message in case:
        result = validates_against_schema('users', example)
        yield assert_equal, result, expected, message


def test_auth_user_validates():
    longer_than_255 = "a" * 256
    exactly_255 = "a" * 255
    case = [
        ({'emailAddress': 'this@that.com',
          'password': exactly_255}, True, "valid"),
        ({'emailAddress': 'thisthat.com',
          'password': exactly_255}, False, "invalid email thisthat.com"),
        ({'emailAddress': 'this@that',
          'password': exactly_255}, False, "invalid email this@that"),
        ({'emailAddress': 'this@t@hat.com',
          'password': exactly_255}, False, "invalid email this@t@hat.com"),
        ({'emailAddress': '',
          'password': exactly_255}, False, "Missing email"),
        ({'emailAddress': 'this@that.com',
          'name': exactly_255}, False, "missing password"),
        ({'emailAddress': 'this@that.com',
          'password': longer_than_255}, False, "too long password"),
        ({'emailAddress': 'this@that.com',
          'password': longer_than_255}, False, "too short password"),
        ({'emailAddress': 'this@that.com',
          'password': ''}, False, "too short password")
    ]

    for example, expected, message in case:
        result = validates_against_schema('users-auth', example)
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


def test_valid_g4_service_has_no_validation_errors():
    data = load_example_listing("G4")
    errs = get_validation_errors("services-g-cloud-4", data)
    assert not errs


def test_valid_g5_service_has_no_validation_errors():
    data = load_example_listing("G5")
    errs = get_validation_errors("services-g-cloud-5", data)
    assert not errs


def test_valid_g6_service_has_no_validation_errors():
    data = load_example_listing("G6-PaaS")
    errs = get_validation_errors("services-g-cloud-6-paas", data)
    assert not errs


def test_valid_g7_service_has_no_validation_errors():
    data = load_example_listing("G7-SCS")
    errs = get_validation_errors("services-g-cloud-7-scs", data)
    assert not errs


def test_g7_missing_required_field_has_validation_error():
    data = load_example_listing("G7-SCS")
    data.pop("serviceSummary", None)
    errs = get_validation_errors("services-g-cloud-7-scs", data)
    assert "answer_required" in errs['serviceSummary']


def test_enforce_required_false_allows_missing_fields():
    data = load_example_listing("G7-SCS")
    data.pop("serviceSummary", None)
    data.pop("serviceDefinitionDocumentURL", None)
    errs = get_validation_errors("services-g-cloud-7-scs", data,
                                 enforce_required=False)
    assert not errs


def test_required_fields_param_requires_specified_fields():
    data = load_example_listing("G7-SCS")
    data.pop("serviceSummary", None)
    data.pop("serviceDefinitionDocumentURL", None)
    errs = get_validation_errors("services-g-cloud-7-scs", data,
                                 enforce_required=False,
                                 required_fields=['serviceSummary'])
    assert "answer_required" in errs['serviceSummary']


def test_additional_properties_has_validation_error():
    data = load_example_listing("G7-SCS")
    data.update({'newKey': 1})
    errs = get_validation_errors("services-g-cloud-7-scs", data)
    assert "Additional properties are not allowed ('newKey' was unexpected)" \
           in "{}".format(errs['_form'])


def test_invalid_enum_values_has_validation_error():
    data = load_example_listing("G7-SCS")
    data.update({'minimumContractPeriod': 'Fortnight'})
    errs = get_validation_errors("services-g-cloud-7-scs", data)
    assert "'Fortnight' is not one of" in errs['minimumContractPeriod']


def test_invalid_url_field_has_validation_error():
    data = load_example_listing("G7-SCS")
    data.update({'serviceDefinitionDocumentURL': 'not_a_url'})
    errs = get_validation_errors("services-g-cloud-7-scs", data)
    assert "'not_a_url' is not" in errs['serviceDefinitionDocumentURL']


def test_too_many_words_causes_validation_error():
    data = load_example_listing("G7-SCS")
    data.update({'serviceBenefits': ['more than ten words 5 6 7 8 9 10 11']})
    errs = get_validation_errors("services-g-cloud-7-scs", data)
    assert "under_10_words" in errs['serviceBenefits']


def test_too_many_list_items_causes_validation_error():
    data = load_example_listing("G7-SCS")
    data.update({'serviceBenefits': [
        '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'
    ]})
    errs = get_validation_errors("services-g-cloud-7-scs", data)
    assert "under_10_items" in errs['serviceBenefits']


def test_string_too_long_causes_validation_error():
    data = load_example_listing("G7-SCS")
    data.update({'serviceName': "a" * 101})
    errs = get_validation_errors("services-g-cloud-7-scs", data)
    assert "under_character_limit" in errs['serviceName']


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
