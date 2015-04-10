import json
import re
import os

from flask import abort
from jsonschema import ValidationError, FormatChecker
from jsonschema.validators import validator_for

MINIMUM_SERVICE_ID_LENGTH = 10
MAXIMUM_SERVICE_ID_LENGTH = 20

JSON_SCHEMAS_PATH = './json_schemas'
FORMAT_CHECKER = FormatChecker()


def load_schemas(schemas_path):
    loaded_schemas = {}
    for schema_file in os.listdir(schemas_path):
        if schema_file.endswith('.json'):
            schema_name = schema_file[:-5]
            with open(os.path.join(schemas_path, schema_file)) as f:
                schema = json.load(f)
                validator = validator_for(schema)
                validator.check_schema(schema)
                loaded_schemas[schema_name] = validator(
                    schema, format_checker=FORMAT_CHECKER)
    return loaded_schemas

SCHEMAS = load_schemas(JSON_SCHEMAS_PATH)


def validate_updater_json_or_400(submitted_json):
    if not validates_against_schema(SCHEMAS['update-details'], submitted_json):
        abort(400, "JSON was not a valid format")


def validate_user_json_or_400(submitted_json):
    if not validates_against_schema(SCHEMAS['users'], submitted_json):
        abort(400, "JSON was not a valid format")


def validate_user_auth_json_or_400(submitted_json):
    try:
        validates_against_schema(SCHEMAS['auth_users'], submitted_json)
    except ValidationError as e:
        abort(400, "JSON was not a valid format. {}".format(e.message))


def detect_framework_or_400(submitted_json):
    framework = detect_framework(submitted_json)
    if not framework:
        abort(400, "JSON was not a valid format. {}".format(
            reason_for_failure(submitted_json))
        )
    return framework


def detect_framework(submitted_json):
    if validates_against_schema('g4-services-schema', submitted_json):
        return 'G-Cloud 4'
    elif validates_against_schema('g5-services-schema', submitted_json):
        return 'G-Cloud 5'
    elif validates_against_schema('g6-scs-schema', submitted_json) or \
            validates_against_schema('g6-saas-schema', submitted_json) or \
            validates_against_schema('g6-paas-schema', submitted_json) or \
            validates_against_schema('g6-iaas-schema', submitted_json):
        return 'G-Cloud 6'
    else:
        return False


def validates_against_schema(validator, submitted_json):
    try:
        if isinstance(validator, basestring):
            validator = SCHEMAS[validator]
    except NameError:
        if isinstance(validator, str):
            validator = SCHEMAS[validator]

    try:
        validator.validate(submitted_json)
    except ValidationError:
        return False
    else:
        return True


def reason_for_failure(submitted_json):
    response = []
    try:
        SCHEMAS['g6-scs-schema'].validate(submitted_json)
    except ValidationError as e1:
        response.append('Not SCS: %s' % e1.message)

    try:
        SCHEMAS['g6-saas-schema'].validate(submitted_json)
    except ValidationError as e2:
        response.append('Not SaaS: %s' % e2.message)

    try:
        SCHEMAS['g6-paas-schema'].validate(submitted_json)
    except ValidationError as e3:
        response.append('Not PaaS: %s' % e3.message)

    try:
        SCHEMAS['g6-iaas-schema'].validate(submitted_json)
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


def is_valid_service_id_or_400(service_id):
    if is_valid_service_id(service_id):
        return True
    else:
        abort(400, "Invalid service ID supplied: %s" % service_id)
