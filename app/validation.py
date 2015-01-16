import json

from flask import abort
from jsonschema import validate, ValidationError


with open("json_schemas/g6-scs-schema.json") as json_file1:
    G6_SCS_SCHEMA = json.load(json_file1)

with open("json_schemas/g6-saas-schema.json") as json_file2:
    G6_SAAS_SCHEMA = json.load(json_file2)

with open("json_schemas/g6-iaas-schema.json") as json_file3:
    G6_IAAS_SCHEMA = json.load(json_file3)

with open("json_schemas/g6-paas-schema.json") as json_file4:
    G6_PAAS_SCHEMA = json.load(json_file4)


def validate_json_or_400(submitted_json):
    if not validate_json(submitted_json):
        abort(400, "JSON was not a valid format")


def validate_json(submitted_json):
    if validates_against_schema(G6_SCS_SCHEMA, submitted_json):
        return 'G6-SCS'
    elif validates_against_schema(G6_SAAS_SCHEMA, submitted_json):
        return 'G6-SaaS'
    elif validates_against_schema(G6_PAAS_SCHEMA, submitted_json):
        return 'G6-PaaS'
    elif validates_against_schema(G6_IAAS_SCHEMA, submitted_json):
        return 'G6-IaaS'
    else:
        # print_reason_for_failure(submitted_json)
        return False


def validates_against_schema(schema, submitted_json):
    try:
        validate(submitted_json, schema)
    except ValidationError:
        return False
    else:
        return True


def print_reason_for_failure(submitted_json):
    print('FAILED TO VALIDATE:')
    print(submitted_json)
    try:
        validate(submitted_json, G6_SCS_SCHEMA)
    except ValidationError as e1:
        print('Not SCS: %s' % e1.message)

    try:
        validate(submitted_json, G6_SAAS_SCHEMA)
    except ValidationError as e2:
        print('Not SaaS: %s' % e2.message)

    try:
        validate(submitted_json, G6_PAAS_SCHEMA)
    except ValidationError as e3:
        print('Not PaaS: %s' % e3.message)

    try:
        validate(submitted_json, G6_IAAS_SCHEMA)
    except ValidationError as e4:
        print('Not IaaS: %s' % e4.message)
