import os
import json
import jsonschema
from jsonschema import validate
from app.services.g6importService import validate_json


def test_all_schemas_are_valid():
    for file_name in os.listdir('schemata'):
        if os.path.isfile('schemata/%s' % file_name):
            print('Testing schema: %s' % file_name)
            json_schema_file = open('schemata/%s' % file_name)
            assert check_schema(json.load(json_schema_file))


def test_example_json_validates_correctly():
    json_scs = json.load(open('example_listings/SSP-JSON-SCS.json'))
    assert validate_json(json_scs) == 'G6-SCS'

    json_scs = json.load(open('example_listings/SSP-JSON-SAAS.json'))
    assert validate_json(json_scs) == 'G6-SaaS'

    json_scs = json.load(open('example_listings/SSP-JSON-PAAS.json'))
    assert validate_json(json_scs) == 'G6-PaaS'

    json_scs = json.load(open('example_listings/SSP-JSON-IAAS.json'))
    assert validate_json(json_scs) == 'G6-IaaS'

    json_scs = json.load(open('example_listings/SSP-INVALID.json'))
    assert validate_json(json_scs) is False


def check_schema(schema):
    try:
        validate({}, schema)
    except jsonschema.SchemaError as ex:
        print('Invalid JSON schema: %s' % ex.message)
        return False
    except jsonschema.ValidationError:
        return True
    else:
        return True
