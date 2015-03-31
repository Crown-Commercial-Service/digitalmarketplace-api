import json

from flask import abort
from jsonschema import validate, ValidationError
from jsonschema.validators import validator_for
import re

MINIMUM_SERVICE_ID_LENGTH = 10
MAXIMUM_SERVICE_ID_LENGTH = 20

with open("json_schemas/g6-scs-schema.json") as json_file1:
    G6_SCS_SCHEMA = json.load(json_file1)
    G6_SCS_VALIDATOR = validator_for(G6_SCS_SCHEMA)
    G6_SCS_VALIDATOR.check_schema(G6_SCS_SCHEMA)
    G6_SCS_VALIDATOR = G6_SCS_VALIDATOR(G6_SCS_SCHEMA)

with open("json_schemas/g6-saas-schema.json") as json_file2:
    G6_SAAS_SCHEMA = json.load(json_file2)
    G6_SAAS_VALIDATOR = validator_for(G6_SAAS_SCHEMA)
    G6_SAAS_VALIDATOR.check_schema(G6_SAAS_SCHEMA)
    G6_SAAS_VALIDATOR = G6_SAAS_VALIDATOR(G6_SAAS_SCHEMA)

with open("json_schemas/g6-iaas-schema.json") as json_file3:
    G6_IAAS_SCHEMA = json.load(json_file3)
    G6_IAAS_VALIDATOR = validator_for(G6_IAAS_SCHEMA)
    G6_IAAS_VALIDATOR.check_schema(G6_IAAS_SCHEMA)
    G6_IAAS_VALIDATOR = G6_IAAS_VALIDATOR(G6_IAAS_SCHEMA)

with open("json_schemas/g6-paas-schema.json") as json_file4:
    G6_PAAS_SCHEMA = json.load(json_file4)
    G6_PAAS_VALIDATOR = validator_for(G6_PAAS_SCHEMA)
    G6_PAAS_VALIDATOR.check_schema(G6_PAAS_SCHEMA)
    G6_PAAS_VALIDATOR = G6_PAAS_VALIDATOR(G6_PAAS_SCHEMA)

with open("json_schemas/update-details.json") as json_file5:
    UPDATER_SCHEMA = json.load(json_file5)
    UPDATER_VALIDATOR = validator_for(UPDATER_SCHEMA)
    UPDATER_VALIDATOR.check_schema(UPDATER_SCHEMA)
    UPDATER_VALIDATOR = UPDATER_VALIDATOR(UPDATER_SCHEMA)

with open("json_schemas/users.json") as json_file6:
    USERS_SCHEMA = json.load(json_file6)
    USERS_VALIDATOR = validator_for(USERS_SCHEMA)
    USERS_VALIDATOR.check_schema(UPDATER_SCHEMA)
    USERS_VALIDATOR = USERS_VALIDATOR(USERS_SCHEMA)

def validate_updater_json_or_400(submitted_json):
    if not validates_against_schema(UPDATER_VALIDATOR, submitted_json):
        abort(400, "JSON was not a valid format")


def validate_json_or_400(submitted_json):
    if not validate_json(submitted_json):
        abort(400, "JSON was not a valid format. {}".format(
            reason_for_failure(submitted_json))
        )


def validate_json(submitted_json):
    if validates_against_schema(G6_SCS_VALIDATOR, submitted_json):
        return 'G6-SCS'
    elif validates_against_schema(G6_SAAS_VALIDATOR, submitted_json):
        return 'G6-SaaS'
    elif validates_against_schema(G6_PAAS_VALIDATOR, submitted_json):
        return 'G6-PaaS'
    elif validates_against_schema(G6_IAAS_VALIDATOR, submitted_json):
        return 'G6-IaaS'
    else:
        return False


def validates_against_schema(validator, submitted_json):
    try:
        validator.validate(submitted_json)
    except ValidationError:
        return False
    else:
        return True


def reason_for_failure(submitted_json):
    response = []
    try:
        validate(submitted_json, G6_SCS_SCHEMA)
    except ValidationError as e1:
        response.append('Not SCS: %s' % e1.message)

    try:
        validate(submitted_json, G6_SAAS_SCHEMA)
    except ValidationError as e2:
        response.append('Not SaaS: %s' % e2.message)

    try:
        validate(submitted_json, G6_PAAS_SCHEMA)
    except ValidationError as e3:
        response.append('Not PaaS: %s' % e3.message)

    try:
        validate(submitted_json, G6_IAAS_SCHEMA)
    except ValidationError as e4:
        response.append('Not IaaS: %s' % e4.message)

    return '. '.join(response)


def is_valid_service_id(service_id):
    """
    Validate that service ids contain only letters
    numbers and dashes. [A-z0-9-]
    :param service_id:
    :return True|False:
    """

    if len(service_id) > MAXIMUM_SERVICE_ID_LENGTH or \
            len(service_id) < MINIMUM_SERVICE_ID_LENGTH or \
            re.search(r"[^A-z0-9-]", service_id):
        return False
    return True
