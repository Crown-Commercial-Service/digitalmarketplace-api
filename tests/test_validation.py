from __future__ import absolute_import

import os
import json

import pytest
import mock
from jsonschema import validate, SchemaError, ValidationError

from app.utils import drop_foreign_fields
from app.validation import (
    validates_against_schema,
    is_valid_service_id,
    is_valid_date,
    is_valid_acknowledged_state,
    get_validation_errors,
    is_valid_email_address,
    is_valid_string,
    min_price_less_than_max_price,
    translate_json_schema_errors,
    buyer_email_address_has_approved_domain,
    is_approved_buyer_domain,
)
from tests.helpers import load_example_listing


def drop_api_exported_fields_so_that_api_import_will_validate(data):
    return drop_foreign_fields(
        data, ['id', 'lot', 'supplierId', 'supplierName', 'links', 'status',
               'frameworkSlug', 'frameworkName', 'lotName', 'createdAt', 'updatedAt'])


def test_supplier_validates():
    data = load_example_listing("supplier_creation")
    errs = get_validation_errors("new-supplier", data)
    assert len(errs) == 0


def test_supplier_validates_with_no_companies_house_number():
    data = load_example_listing("supplier_creation")
    data.pop("companiesHouseNumber", None)
    errs = get_validation_errors("new-supplier", data)
    assert len(errs) == 0


def test_supplier_fails_with_bad_companies_house_number():
    data = load_example_listing("supplier_creation")
    data["companiesHouseNumber"] = "short"
    errs = get_validation_errors("new-supplier", data)
    assert len(errs) == 1


@pytest.mark.parametrize(
    'duns', ['12345678', '1234567890']
)
def test_new_supplier_fails_with_bad_duns(duns):
    data = load_example_listing("new-supplier")
    data["dunsNumber"] = duns
    errs = get_validation_errors("new-supplier", data)
    assert len(errs) == 1


def test_for_valid_date():
    cases = [
        ("2010-01-01", True),
        ("2010-02-29", False),
        ("invalid", False)
    ]

    for example, expected in cases:
        assert is_valid_date(example) == expected


def test_for_valid_acknowledged_state():
    cases = [
        ("all", True),
        ("true", True),
        ("false", True),
        ("2010-02-29", False),
        ("invalid", False)
    ]

    for example, expected in cases:
        assert is_valid_acknowledged_state(example) == expected


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
        assert is_valid_service_id(example) == expected


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
        assert is_valid_string(example, min, max) == expected


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

    assert validates_against_schema('services-update', invalid_updater_no_fields) is False
    assert validates_against_schema('services-update', invalid_updater_extra_fields) is True
    assert validates_against_schema('services-update', invalid_updater_only_invalid_fields) is False
    assert validates_against_schema('services-update', valid_updater) is True


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
        assert result == expected


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
        assert result == expected


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

        assert 'max_less_than_min' == errs['priceMax']


def test_max_price_larger_than_min_price():
    cases = ['132.20', '']

    for price_max in cases:
        data = load_example_listing("G7-SCS")
        data.update({"priceMax": price_max})
        errs = get_validation_errors("services-g-cloud-7-scs", data)

        assert 'priceMax' not in errs


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
    assert errors == {'developerPriceMax': 'max_less_than_min'}


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
    assert errors == {'developerPriceMax': 'max_less_than_min', 'designerPriceMax': 'max_less_than_min'}


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
    assert errors == {'developerPriceMax': 'max_less_than_min'}


@pytest.mark.parametrize("schema_name", (
    "brief-responses-digital-outcomes-and-specialists-digital-specialists",
    "brief-responses-digital-outcomes-and-specialists-2-digital-specialists",
))
def test_brief_response_essential_requirements(schema_name):
    assert get_validation_errors(
        schema_name,
        {
            "availability": "valid start date",
            "dayRate": "100",
            "essentialRequirementsMet": True,
            "essentialRequirements": [
                {"evidence": "valid evidence"},
                {"evidence": "word " * 100},
                {"evidence": "some more valid evidence"},
                {},
            ],
            "niceToHaveRequirements": [
                {"yesNo": False},
            ],
            "respondToEmailAddress": "valid@email.com",
        },
    ) == {
        'essentialRequirements': [
            {
                'error': 'under_100_words',
                'field': 'evidence',
                'index': 1,
            },
            {
                'error': 'answer_required',
                'field': 'evidence',
                'index': 3,
            },
        ],
    }


@pytest.mark.parametrize("schema_name", (
    "brief-responses-digital-outcomes-and-specialists-digital-specialists",
    "brief-responses-digital-outcomes-and-specialists-2-digital-specialists",
))
class TestBriefResponseNiceToHaveRequirements:
    def setup_method(self, method):
        self.data = {
            "availability": "valid start date",
            "dayRate": "100",
            "essentialRequirementsMet": True,
            "essentialRequirements": [
                {"evidence": "valid evidence"},
            ],
            "respondToEmailAddress": "valid@email.com",
        }

    def test_nice_to_have_optional(self, schema_name):
        assert not get_validation_errors(schema_name, self.data)

    def test_error_messages(self, schema_name):
        self.data["niceToHaveRequirements"] = [
            {},
            {"yesNo": True, "evidence": "valid evidence"},
            {"yesNo": True, "evidence": "word " * 100},
            {"yesNo": True},
            {"yesNo": False},
            {"yesNo": False, "evidence": "shouldnt be here"},
        ]
        assert get_validation_errors(schema_name, self.data)["niceToHaveRequirements"] == [
            {
                'error': 'answer_required',
                'field': 'yesNo',
                'index': 0
            },
            {
                'error': 'under_100_words',
                'field': 'evidence',
                'index': 2
            },
            {
                'error': 'answer_required',
                'field': 'evidence',
                'index': 3
            },
            {
                'error': (
                    # python 3.6+ guarantees consistent dict ordering
                    "{'yesNo': False, 'evidence': 'shouldnt be here'} is not valid under any of the given schemas"
                ),
                'index': 5,
            },
        ]

    def test_pure_booleans(self, schema_name):
        self.data["niceToHaveRequirements"] = [True, True, True]
        assert get_validation_errors(schema_name, self.data)["niceToHaveRequirements"] == "True is not of type 'object'"

    def test_dict_bool_mix(self, schema_name):
        self.data["niceToHaveRequirements"] = [
            {"yesNo": False, "evidence": "shouldnt be here"},
            True,
            {'yesNo': False},
            {"yesNo": False, "evidence": "shouldnt be here"},
        ]
        assert get_validation_errors(schema_name, self.data)["niceToHaveRequirements"] == "True is not of type 'object'"


@pytest.mark.parametrize("schema_name", ("services-g-cloud-9-cloud-software", "services-g-cloud-9-cloud-hosting"))
@pytest.mark.parametrize("required_fields,input_data,expected_errors", (
    # Valid responses for boolean question with followup:
    (["freeVersionTrial"], {"freeVersionTrialOption": False}, {}),
    (
        ["freeVersionTrialOption"],
        {
            "freeVersionTrialOption": True,
            "freeVersionDescription": "description",
            "freeVersionLink": "https://gov.uk",
        },
        {},
    ),
    # Missing followup answers:
    (
        ["freeVersionTrialOption"],
        {"freeVersionTrialOption": True},
        {"freeVersionDescription": "answer_required"},
    ),
    (
        ["freeVersionTrialOption"],
        {"freeVersionTrialOption": True, "freeVersionLink": "https://gov.uk"},
        {"freeVersionDescription": "answer_required"},
    ),
    # Missing followup question is not required if it's optional:
    (
        ["freeVersionTrialOption"],
        {"freeVersionTrialOption": True, "freeVersionDescription": "description"},
        {},
    ),
    # Followup answers when none should be present. These return the original
    # schema error since they shouldn't happen when request is coming from the
    # frontend app so we don't need to display an error message.
    (
        ["freeVersionTrialOption"],
        {
            "freeVersionTrialOption": False,
            "freeVersionLink": "https://gov.uk",
        },
        {'_form': ['{} is not valid under any of the given schemas'.format({
            "freeVersionTrialOption": False,
            "freeVersionLink": "https://gov.uk",
        })]},
    ),
    (
        ["freeVersionTrialOption"],
        {
            "freeVersionTrialOption": False,
            "freeVersionDescription": "description",
        },
        {'_form': [u'{} is not valid under any of the given schemas'.format({
            "freeVersionTrialOption": False,
            "freeVersionDescription": "description",
        })]},
    ),
    # Followup answers when the original question answer is missing
    (
        ["freeVersionTrialOption"],
        {"freeVersionDescription": "description", "freeVersionLink": "https://gov.uk"},
        {"freeVersionTrialOption": "answer_required"},
    ),
    # Valid responses for checkbox question with followups
    (
        ["securityGovernanceStandards"],
        {"securityGovernanceAccreditation": True, "securityGovernanceStandards": ["csa_ccm"]},
        {},
    ),
    (
        ["securityGovernanceStandards"],
        {"securityGovernanceAccreditation": False, "securityGovernanceApproach": "some other approach"},
        {},
    ),
    (
        ["securityGovernanceStandards"],
        {
            "securityGovernanceAccreditation": True,
            "securityGovernanceStandards": ["csa_ccm", "other"],
            "securityGovernanceStandardsOther": "some other standards",
        },
        {},
    ),
    # Missing followup answers for checkbox question
    (
        ["securityGovernanceStandards"],
        {"securityGovernanceAccreditation": True, "securityGovernanceStandards": ["csa_ccm", "other"]},
        {"securityGovernanceStandardsOther": "answer_required"},
    ),
    # Followup answers when none should be present
    (
        ["securityGovernanceStandards"],
        {
            "securityGovernanceAccreditation": True,
            "securityGovernanceStandards": ["csa_ccm"],
            "securityGovernanceStandardsOther": "some other standards",
        },
        {"_form": [u'{} is not valid under any of the given schemas'.format({
            "securityGovernanceAccreditation": True,
            "securityGovernanceStandards": ["csa_ccm"],
            "securityGovernanceStandardsOther": "some other standards",
        })]},
    ),
    # Followup answers when the original question answer is missing
    (
        ["securityGovernanceAccreditation"],
        {"securityGovernanceStandards": ["csa_ccm"]},
        {"securityGovernanceAccreditation": "answer_required"},
    ),
    (
        ["securityGovernanceStandards"],
        {"securityGovernanceStandardsOther": "some other standards"},
        {"securityGovernanceStandards": "answer_required"},
    ),
))
def test_g9_followup_questions(schema_name, required_fields, input_data, expected_errors):
    assert get_validation_errors(
        schema_name,
        input_data,
        enforce_required=False,
        required_fields=required_fields,
    ) == expected_errors


@pytest.mark.parametrize("required_fields,input_data,expected_errors", (
    (
        ["openStandardsPrinciples", "dataProtocols"],
        {
            "openStandardsPrinciples": True,
            "dataProtocols": True,
            "designerPriceMax": "900",
        },
        {},
    ),
    # by including designerPriceMax in the required_fields we're stating that its dependencies must also be satisfied
    (
        ["openStandardsPrinciples", "dataProtocols", "designerPriceMax"],
        {
            "openStandardsPrinciples": True,
            "dataProtocols": True,
            "designerPriceMax": "900",
        },
        {
            'designerAccessibleApplications': 'answer_required',
            'designerLocations': 'answer_required',
            'designerPriceMin': 'answer_required',
        },
    ),
))
def test_dos4_dependent_questions(required_fields, input_data, expected_errors):
    # specifically dos4 services because they have "dependencies"
    assert get_validation_errors(
        "services-digital-outcomes-and-specialists-4-digital-specialists",
        input_data,
        enforce_required=False,
        required_fields=required_fields,
    ) == expected_errors


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


def test_translate_social_value_oneof_errors():
    assert api_error([{
        'validator': 'oneOf',
        'message': "failed",
        'path': ['socialValue'],
        'validator_value': [{'maximum': 20, 'minimum': 10, 'type': 'integer'},
                            {'maximum': 0, 'minimum': 0, 'type': 'integer'}],
        'context': [
            {'message': "failed",
             'validator': 'oneOf'
             }
        ],
    }]) == {'socialValue': 'not_a_number'}


def test_translate_unknown_oneof_error():
    assert api_error([{
        'validator': 'oneOf',
        'message': "failed",
        'path': ['example', 0],
        'context': [
            {'message': "Unknown type", 'validator': 'type'}
        ],
    }]) == {'example': [{'error': 'failed', 'index': 0}]}


@pytest.mark.parametrize(
    'email, expected_result', [
        ('hurray@cool.gov', True), ('hurray@very.cool.gov', True), ('hurray@notcool.gov', False)
    ]
)
def test_buyer_email_address_has_approved_domain(email, expected_result):
    existing_domains = [
        mock.Mock(domain_name='cool.gov')
    ]

    assert buyer_email_address_has_approved_domain(existing_domains, email) == expected_result


@pytest.mark.parametrize(
    'domain, expected_result', [
        ('cool.gov', True), ('very.cool.gov', True), ('notcool.gov', False)
    ]
)
def test_is_approved_buyer_domain(domain, expected_result):
    existing_domains = [
        mock.Mock(domain_name='cool.gov')
    ]

    assert is_approved_buyer_domain(existing_domains, domain) == expected_result


@pytest.mark.parametrize(
    ("email_address", "is_valid"),
    (
        ("me@example.com", True),
        ("very.common@example.com", True),
        ("disposable.style.email.with+symbol@example.com", True),
        ("", False),
        ("Abc.example.com", False),
        ("email-address-with-NUL\x00@example.com", False),
        (r'a"b(c)d,e:f;g<h>i[j\k]l@example.com', False),
    ))
def test_is_valid_email_address(email_address, is_valid):
    assert is_valid_email_address(email_address) is is_valid
