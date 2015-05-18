import json
import re
import os

from flask import abort
from jsonschema import ValidationError, FormatChecker
from jsonschema.validators import validator_for

MINIMUM_SERVICE_ID_LENGTH = 10
MAXIMUM_SERVICE_ID_LENGTH = 20

JSON_SCHEMAS_PATH = './json_schemas'
SCHEMA_NAMES = [
    'services-g4',
    'services-g5',
    'services-g6-scs',
    'services-g6-saas',
    'services-g6-paas',
    'services-g6-iaas',
    'services-update',
    'users',
    'users-auth',
    'suppliers'
]
FORMAT_CHECKER = FormatChecker()


def load_schemas(schemas_path, schema_names):
    loaded_schemas = {}
    for schema_name in schema_names:
        schema_path = os.path.join(schemas_path, '{}.json'.format(schema_name))

        with open(schema_path) as f:
            schema = json.load(f)
            validator = validator_for(schema)
            validator.check_schema(schema)
            loaded_schemas[schema_name] = schema
    return loaded_schemas

_SCHEMAS = load_schemas(JSON_SCHEMAS_PATH, SCHEMA_NAMES)


def get_validator(schema_name):
    schema = _SCHEMAS[schema_name]
    return validator_for(schema)(schema, format_checker=FORMAT_CHECKER)


def validate_updater_json_or_400(submitted_json):
    if not validates_against_schema('services-update', submitted_json):
        abort(400, "JSON was not a valid format")


def validate_user_json_or_400(submitted_json):
    if not validates_against_schema('users', submitted_json):
        abort(400, "JSON was not a valid format")
    if submitted_json['role'] == 'supplier' \
            and 'supplierId' not in submitted_json:
        abort(400, "No supplier id provided for supplier user")


def validate_user_auth_json_or_400(submitted_json):
    try:
        validates_against_schema('users-auth', submitted_json)
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
    if validates_against_schema('services-g4', submitted_json):
        return 'G-Cloud 4'
    elif validates_against_schema('services-g5', submitted_json):
        return 'G-Cloud 5'
    elif validates_against_schema('services-g6-scs', submitted_json) or \
            validates_against_schema('services-g6-saas', submitted_json) or \
            validates_against_schema('services-g6-paas', submitted_json) or \
            validates_against_schema('services-g6-iaas', submitted_json):
        return 'G-Cloud 6'
    else:
        return False


def validate_supplier_json_or_400(submitted_json):
    try:
        get_validator('suppliers').validate(submitted_json)
    except ValidationError as e:
        abort(400, "JSON was not a valid format. {}".format(e.message))


def validates_against_schema(validator_name, submitted_json):
    try:
        get_validator(validator_name).validate(submitted_json)
    except ValidationError:
        return False
    else:
        return True


def reason_for_failure(submitted_json):
    response = []
    try:
        get_validator('services-g4').validate(submitted_json)
    except ValidationError as e1:
        response.append('Not G4: %s' % e1.message)

    try:
        get_validator('services-g5').validate(submitted_json)
    except ValidationError as e1:
        response.append('Not G5: %s' % e1.message)

    try:
        get_validator('services-g6-scs').validate(submitted_json)
    except ValidationError as e1:
        response.append('Not SCS: %s' % e1.message)

    try:
        get_validator('services-g6-saas').validate(submitted_json)
    except ValidationError as e2:
        response.append('Not SaaS: %s' % e2.message)

    try:
        get_validator('services-g6-paas').validate(submitted_json)
    except ValidationError as e3:
        response.append('Not PaaS: %s' % e3.message)

    try:
        get_validator('services-g6-iaas').validate(submitted_json)
    except ValidationError as e4:
        response.append('Not IaaS: %s' % e4.message)

    return '. '.join(response)


def is_valid_service_id(service_id):
    """
    Validate that service ids contain only letters
    numbers and dashes ([A-z0-9-]) and that they're
    less than | equal to `MINIMUM_SERVICE_ID_LENGTH`
    greater than | equal to `MAXIMUM_SERVICE_ID_LENGTH`
    :param service_id:
    :return True|False:
    """

    regex_match_valid_service_id = r"^[A-z0-9-]{%s,%s}$" % (
        MINIMUM_SERVICE_ID_LENGTH,
        MAXIMUM_SERVICE_ID_LENGTH
    )

    if re.search(regex_match_valid_service_id, service_id):
        return True

    return False


def is_valid_service_id_or_400(service_id):
    if is_valid_service_id(service_id):
        return True
    else:
        abort(400, "Invalid service ID supplied: %s" % service_id)
