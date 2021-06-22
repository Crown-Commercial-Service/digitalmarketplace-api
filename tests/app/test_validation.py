import os
import json

from nose.tools import assert_equal, assert_in, assert_not_in
from jsonschema import validate, SchemaError, ValidationError

from app.utils import drop_foreign_fields
from app.validation import validates_against_schema, is_valid_service_id, is_valid_date, \
    is_valid_acknowledged_state, get_validation_errors, is_valid_string, min_price_less_than_max_price

EXAMPLE_LISTING_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                    '..', '..', 'example_listings'))


def drop_api_exported_fields_so_that_api_import_will_validate(data):
    return drop_foreign_fields(
        data, ['id', 'lot', 'supplierCode', 'supplierName', 'links', 'status',
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
        assert_equal(is_valid_date(example), expected, example)


def test_for_valid_acknowledged_state():
    cases = [
        ("all", True),
        ("true", True),
        ("false", True),
        ("2010-02-29", False),
        ("invalid", False)
    ]

    for example, expected in cases:
        assert_equal(is_valid_acknowledged_state(example), expected)


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
        assert_equal(is_valid_service_id(example), expected, example)


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

    for example, vmin, vmax, expected in cases:
        assert_equal(is_valid_string(
            example, vmin, vmax), expected, example)


def test_all_schemas_are_valid():
    for file_name in os.listdir('json_schemas'):
        file_path = 'json_schemas/%s' % file_name
        if os.path.isfile(file_path) and file_path.endswith(".json"):
            check_schema_file(file_path)


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
          'supplierCode': 123,
          'password': exactly_255}, True, "valid supplier id"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': exactly_255,
          'supplierCode': '',
          'password': exactly_255}, False, "invalid supplier id (to short)"),
        ({'emailAddress': 'this@that.com',
          'role': 'buyer',
          'name': exactly_255,
          'supplierCode': longer_than_255,
          'password': exactly_255}, False, "invalid supplier id (to long)")
    ]

    for example, expected, message in case:
        result = validates_against_schema('users', example)
        assert_equal(result, expected, message)


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
        assert_equal(result, expected, message)


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
    assert 'under_word_limit' in errs['serviceBenefits']


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

    check_min_price_error('priceMin', "")

    for case in cases:
        check_min_price_error('priceMin', case)
        check_min_price_error('priceMax', case)


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

    check_min_price_valid('priceMax', "")

    for case in cases:
        check_min_price_valid('priceMin', case)
        check_min_price_valid('priceMax', case)


def test_min_price_larger_than_max_price_causes_validation_error():
    cases = ['32.20', '9.00']

    for price_max in cases:
        data = load_example_listing("G7-SCS")
        data.update({"priceMax": price_max})
        errs = get_validation_errors("services-g-cloud-7-scs", data)

        assert_in('max_less_than_min', errs['priceMax'])


def test_max_price_larger_than_min_price():
    cases = ['132.20', '']

    for price_max in cases:
        data = load_example_listing("G7-SCS")
        data.update({"priceMax": price_max})
        errs = get_validation_errors("services-g-cloud-7-scs", data)

        assert_not_in('priceMax', errs)


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


def test_api_type_is_optional():
    data = load_example_listing("G6-PaaS")
    del data["apiType"]
    errs = get_validation_errors("services-g-cloud-7-paas", data)

    assert not errs.get('apiType', None)


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
        try:
            msg = ex.message
        except AttributeError:
            msg = str(ex)

        print('Invalid JSON schema: %s' % msg)
        return False
    except ValidationError:
        return True
    else:
        return True
