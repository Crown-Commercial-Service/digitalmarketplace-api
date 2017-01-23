from __future__ import absolute_import

import os
import json

import pytest
from nose.tools import assert_equal, assert_in, assert_not_in
from jsonschema import validate, SchemaError, ValidationError

from app.utils import drop_foreign_fields
from app.validation import validates_against_schema, is_valid_service_id, is_valid_date, \
    is_valid_acknowledged_state, get_validation_errors, is_valid_string, min_price_less_than_max_price, \
    is_valid_buyer_email, translate_json_schema_errors
from tests.helpers import load_example_listing


def drop_api_exported_fields_so_that_api_import_will_validate(data):
    return drop_foreign_fields(
        data, ['id', 'lot', 'supplierId', 'supplierName', 'links', 'status',
               'frameworkSlug', 'frameworkName', 'lotName', 'createdAt', 'updatedAt'])


def test_supplier_validates():
    data = load_example_listing("supplier_creation")
    errs = get_validation_errors("new-supplier", data)
    assert len(errs) is 0


def test_supplier_validates_with_no_companies_house_number():
    data = load_example_listing("supplier_creation")
    data.pop("companiesHouseNumber", None)
    errs = get_validation_errors("new-supplier", data)
    assert len(errs) is 0


def test_supplier_fails_with_bad_companies_house_number():
    data = load_example_listing("supplier_creation")
    data["companiesHouseNumber"] = "short"
    errs = get_validation_errors("new-supplier", data)
    assert len(errs) is 1


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


def test_valid_g4_service_has_no_validation_errors():
    data = load_example_listing("G4")
    data = drop_api_exported_fields_so_that_api_import_will_validate(data)
    errs = get_validation_errors("services-g-cloud-4", data)
    assert not errs


def test_valid_g5_service_has_no_validation_errors():
    data = load_example_listing("G5")
    data = drop_api_exported_fields_so_that_api_import_will_validate(data)
    errs = get_validation_errors("services-g-cloud-5", data)
    assert not errs


def test_valid_g6_service_has_no_validation_errors():
    data = load_example_listing("G6-PaaS")
    data = drop_api_exported_fields_so_that_api_import_will_validate(data)
    errs = get_validation_errors("services-g-cloud-6-paas", data)
    assert not errs


def test_valid_g7_service_has_no_validation_errors():
    data = load_example_listing("G7-SCS")
    data = drop_api_exported_fields_so_that_api_import_will_validate(data)
    errs = get_validation_errors("services-g-cloud-7-scs", data)
    assert not errs


def test_g7_missing_required_field_has_validation_error():
    data = load_example_listing("G7-SCS")
    data.pop("serviceSummary", None)
    errs = get_validation_errors("services-g-cloud-7-scs", data)
    assert "answer_required" in errs['serviceSummary']


def test_enforce_required_false_allows_missing_fields():
    data = load_example_listing("G7-SCS")
    data = drop_api_exported_fields_so_that_api_import_will_validate(data)
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
    data = drop_api_exported_fields_so_that_api_import_will_validate(data)
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
    assert errs['serviceDefinitionDocumentURL'] == 'invalid_format'


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
    assert "max_items_limit" in errs['serviceBenefits']


def test_string_too_long_causes_validation_error():
    data = load_example_listing("G7-SCS")
    data.update({'serviceName': "a" * 101})
    errs = get_validation_errors("services-g-cloud-7-scs", data)
    assert "under_character_limit" in errs['serviceName']


def test_percentage_out_of_range_causes_validation_error():
    data = load_example_listing("G6-PaaS")
    data.update({'serviceAvailabilityPercentage':
                {"value": 101, "assurance": "Service provider assertion"}})
    errs = get_validation_errors("services-g-cloud-7-paas", data)
    assert "not_a_number" in errs['serviceAvailabilityPercentage']


def test_assurance_only_causes_validation_error():
    data = load_example_listing("G6-PaaS")
    data.update({'serviceAvailabilityPercentage':
                {"assurance": "Service provider assertion"}})
    errs = get_validation_errors("services-g-cloud-7-paas", data)
    assert "answer_required" in errs['serviceAvailabilityPercentage']


def test_non_number_value_causes_validation_error():
    data = load_example_listing("G6-PaaS")
    data.update({'serviceAvailabilityPercentage': {"value": "a99.9", "assurance": "Service provider assertion"}})
    errs = get_validation_errors("services-g-cloud-7-paas", data)
    assert "not_a_number" in errs['serviceAvailabilityPercentage']


def test_value_only_causes_validation_error():
    data = load_example_listing("G6-PaaS")
    data.update({'serviceAvailabilityPercentage': {"value": 99.9}})
    errs = get_validation_errors("services-g-cloud-7-paas", data)
    assert "assurance_required" in errs['serviceAvailabilityPercentage']


def test_price_not_money_format_validation_error():
    cases = [
        "foo",  # not numeric
        "12.",  # too few decimal places
        "12.000001",  # too many decimal places
        ".1",  # too few digits
    ]
    data = load_example_listing("G7-SCS")

    def check_min_price_error(field, case):
        data[field] = case
        errs = get_validation_errors("services-g-cloud-7-scs", data)
        assert field in errs
        assert "not_money_format" in errs[field]

    yield check_min_price_error, 'priceMin', ""

    for case in cases:
        yield check_min_price_error, 'priceMin', case
        yield check_min_price_error, 'priceMax', case


def test_price_not_money_format_valid_cases():
    cases = [
        '12',
        '12.1',
        '12.11',
        '12.111',
        '12.1111',
        '12.11111',
    ]
    data = load_example_listing("G7-SCS")

    def check_min_price_valid(field, case):
        data[field] = case
        errs = get_validation_errors("services-g-cloud-7-scs", data)
        assert "not_money_format" not in errs.get(field, "")

    yield check_min_price_valid, 'priceMax', ""

    for case in cases:
        yield check_min_price_valid, 'priceMin', case
        yield check_min_price_valid, 'priceMax', case


def test_min_price_larger_than_max_price_causes_validation_error():
    cases = ['32.20', '9.00']

    for price_max in cases:
        data = load_example_listing("G7-SCS")
        data.update({"priceMax": price_max})
        errs = get_validation_errors("services-g-cloud-7-scs", data)

        yield assert_in, 'max_less_than_min', errs['priceMax']


def test_max_price_larger_than_min_price():
    cases = ['132.20', '']

    for price_max in cases:
        data = load_example_listing("G7-SCS")
        data.update({"priceMax": price_max})
        errs = get_validation_errors("services-g-cloud-7-scs", data)

        yield assert_not_in, 'priceMax', errs


def test_max_price_larger_than_min_price_with_multiple_price_fields():
    data = {
        'agileCoachPriceMin': '200',
        'agileCoachPriceMax': '250',
        'developerPriceMin': '200',
        'developerPriceMax': '25',
        'windowCleanerPriceMin': '12.50',
        'windowCleanerPriceMax': '300',
    }
    errors = min_price_less_than_max_price({}, data)
    assert_equal(errors, {'developerPriceMax': 'max_less_than_min'})


def test_max_price_larger_than_min_price_with_multiple_price_errors():
    data = {
        'agileCoachPriceMin': '200',
        'agileCoachPriceMax': '250',
        'developerPriceMin': '200',
        'developerPriceMax': '25',
        'designerPriceMin': '300',
        'designerPriceMax': '299.99',
        'windowCleanerPriceMin': '12.50',
        'windowCleanerPriceMax': '300',
    }
    errors = min_price_less_than_max_price({}, data)
    assert_equal(errors, {'developerPriceMax': 'max_less_than_min', 'designerPriceMax': 'max_less_than_min'})


def test_max_price_larger_than_min_does_not_overwrite_previous_errors():
    data = {
        'agileCoachPriceMin': '200',
        'agileCoachPriceMax': '250',
        'developerPriceMin': '200',
        'developerPriceMax': '25',
        'designerPriceMin': '300',
        'designerPriceMax': '299.99',
        'windowCleanerPriceMin': '12.50',
        'windowCleanerPriceMax': '300',
    }
    previous_errors = {'designerPriceMax': 'non_curly_quotes'}
    errors = min_price_less_than_max_price(previous_errors, data)
    assert_equal(errors, {'developerPriceMax': 'max_less_than_min'})


def test_brief_response_essential_requirements():
    assert get_validation_errors(
        "brief-responses-digital-outcomes-and-specialists-digital-specialists",
        {
            "availability": "valid start date",
            "dayRate": "100",
            "essentialRequirementsMet": True,
            "essentialRequirements": [
                {"evidence": "valid evidence"},
                {"evidence": "word " * 100},
                {"evidence": "some more valid evidence"},
                {}
            ],
            "niceToHaveRequirements": [
                {"yesNo": False}
            ],
            "respondToEmailAddress": "valid@email.com"
        }
    ) == {
        'essentialRequirements': [
            {
                'error': 'under_100_words',
                'field': u'evidence',
                'index': 1
            },
            {
                'error': 'answer_required',
                'field': u'evidence',
                'index': 3
            },
        ]
    }


def test_brief_response_nice_to_have_requirements():
    schema_name = "brief-responses-digital-outcomes-and-specialists-digital-specialists"
    data = {
        "availability": "valid start date",
        "dayRate": "100",
        "essentialRequirementsMet": True,
        "essentialRequirements": [
            {"evidence": "valid evidence"},
        ],
        "respondToEmailAddress": "valid@email.com"
    }

    # Nice-to-have requirements are optional.
    assert not get_validation_errors(schema_name, data)

    data["niceToHaveRequirements"] = [
        {},
        {"yesNo": True, "evidence": "valid evidence"},
        {"yesNo": True, "evidence": "word " * 100},
        {"yesNo": True},
        {"yesNo": False},
        {"yesNo": False, "evidence": "shouldnt be here"}
    ]
    error_messages = get_validation_errors(schema_name, data)["niceToHaveRequirements"]
    assert error_messages[:3] == [
        {
            'error': 'answer_required',
            'field': u'yesNo',
            'index': 0
        },
        {
            'error': 'under_100_words',
            'field': u'evidence',
            'index': 2
        },
        {
            'error': 'answer_required',
            'field': u'evidence',
            'index': 3
        }
    ]
    assert error_messages[3]["index"] == 5
    # Python 3 dictionary ordering is unpredicatable so we have to cover both possible orders as it is converted to
    # a string
    assert error_messages[3]["error"] in [
        "{'yesNo': False, 'evidence': 'shouldnt be here'} is not valid under any of the given schemas",
        "{'evidence': 'shouldnt be here', 'yesNo': False} is not valid under any of the given schemas"
    ]
    assert len(error_messages) == 4

    # Purely boolean nice to have requirements
    data["niceToHaveRequirements"] = [True, True, True]
    error_messages = get_validation_errors(schema_name, data)["niceToHaveRequirements"]
    assert "True is not of type" in error_messages
    assert "object" in error_messages

    # Mix of dict and boolean nice to have requirements
    data["niceToHaveRequirements"] = [
        {"yesNo": False, "evidence": "shouldnt be here"},
        True,
        {'yesNo': False},
        {"yesNo": False, "evidence": "shouldnt be here"}
    ]
    error_messages = get_validation_errors(schema_name, data)["niceToHaveRequirements"]
    assert "True is not of type" in error_messages
    assert "object" in error_messages


def test_api_type_is_optional():
    data = load_example_listing("G6-PaaS")
    del data["apiType"]
    errs = get_validation_errors("services-g-cloud-7-paas", data)

    assert not errs.get('apiType', None)


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


@pytest.mark.parametrize('email,expected', [
    ('test@example.com', False),
    ('test@gov.uk', True),
    ('test@something.gov.uk', True),
    ('test@somegov.uk', False),
    ('test@gov.ok', False),
    ('test@test@gov.uk', True)
])
def test_is_valid_buyer_email(email, expected):
    assert is_valid_buyer_email(email) == expected


def api_error(errors):
    schema_errors = []
    for error_data in errors:
        context_errors = []
        for context_error in error_data.get('context', []):
            context_errors.append(
                ValidationError(message=context_error['message'], validator=context_error['validator'])
            )

        error_data['context'] = context_errors

        schema_errors.append(ValidationError(**error_data))

    return translate_json_schema_errors(schema_errors, {})


def test_translate_oneof_errors():
    assert api_error([{
        'validator': 'oneOf',
        'message': "failed",
        'path': ['example', 0],
        'context': [
            {'message': "'example-field' required", 'validator': 'required'}
        ],
    }]) == {'example': [{'error': 'answer_required', 'field': 'example-field', 'index': 0}]}


def test_translate_unknown_oneoff_eerror():
    assert api_error([{
        'validator': 'oneOf',
        'message': "failed",
        'path': ['example', 0],
        'context': [
            {'message': "Unknown type", 'validator': 'type'}
        ],
    }]) == {'example': [{'error': 'failed', 'index': 0}]}
