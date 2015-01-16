from __future__ import absolute_import

import os
import json

from jsonschema import validate, SchemaError, ValidationError

from app.lib.validation import validate_json


def test_all_schemas_are_valid():
    for file_name in os.listdir('json_schemas'):
        if os.path.isfile('json_schemas/%s' % file_name):
            print('Testing schema: %s' % file_name)
            with open('json_schemas/%s' % file_name) as json_schema_file:
                assert check_schema(json.load(json_schema_file))


def test_example_json_validates_correctly():
    with open('example_listings/SSP-JSON-SCS.json') as json_file:
        json_scs = json.load(json_file)
        assert validate_json(json_scs) == 'G6-SCS'

    with open('example_listings/SSP-JSON-SAAS.json') as json_file:
        json_scs = json.load(json_file)
        assert validate_json(json_scs) == 'G6-SaaS'

    with open('example_listings/SSP-JSON-PAAS.json') as json_file:
        json_scs = json.load(json_file)
        assert validate_json(json_scs) == 'G6-PaaS'

    with open('example_listings/SSP-JSON-IAAS.json') as json_file:
        json_scs = json.load(json_file)
        assert validate_json(json_scs) == 'G6-IaaS'

    with open('example_listings/SSP-INVALID.json') as json_file:
        json_scs = json.load(json_file)
        assert validate_json(json_scs) is False


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
