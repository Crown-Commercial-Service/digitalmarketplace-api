import json
import jsonschema
from jsonschema import validate

with open("schemata/g6-scs-schema.json") as json_file1:
    G6_SCS_SCHEMA = json.load(json_file1)

with open("schemata/g6-saas-schema.json") as json_file2:
    G6_SAAS_SCHEMA = json.load(json_file2)

with open("schemata/g6-iaas-schema.json") as json_file3:
    G6_IAAS_SCHEMA = json.load(json_file3)

with open("schemata/g6-paas-schema.json") as json_file4:
    G6_PAAS_SCHEMA = json.load(json_file4)


def validate_json(submitted_json):
    if validates_against_schema(G6_SCS_SCHEMA,submitted_json):
        return 'G6-SCS'
    elif validates_against_schema(G6_SAAS_SCHEMA,submitted_json):
        return 'G6-SaaS'
    elif validates_against_schema(G6_PAAS_SCHEMA,submitted_json):
        return 'G6-PaaS'
    elif validates_against_schema(G6_IAAS_SCHEMA,submitted_json):
        return 'G6-IaaS'
    else:
        print 'Failed validation'
        return False


def validates_against_schema(schema, submitted_json):
    try:
        validate(submitted_json, schema)
    except jsonschema.ValidationError:
        return False
    else:
        return True
