import json
import re
import os

from flask import abort
from jsonschema import ValidationError, FormatChecker
from jsonschema.validators import validator_for
from datetime import datetime
from dmutils.formats import DATE_FORMAT

MINIMUM_SERVICE_ID_LENGTH = 10
MAXIMUM_SERVICE_ID_LENGTH = 20

JSON_SCHEMAS_PATH = './json_schemas'
SCHEMA_NAMES = [
    'services-g-cloud-4',
    'services-g-cloud-5',
    'services-g-cloud-6-iaas',
    'services-g-cloud-6-saas',
    'services-g-cloud-6-paas',
    'services-g-cloud-6-scs',
    'services-g-cloud-7-iaas',
    'services-g-cloud-7-saas',
    'services-g-cloud-7-paas',
    'services-g-cloud-7-scs',
    'services-update',
    'users',
    'users-auth',
    'suppliers',
    'contact-information',
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


def get_validator(schema_name, enforce_required=True, required_fields=None):
    if required_fields is None:
        required_fields = []
    if enforce_required:
        schema = _SCHEMAS[schema_name]
    else:
        schema = _SCHEMAS[schema_name].copy()
        schema['required'] = [
            field for field in schema.get('required', [])
            if field in required_fields
            ]
    return validator_for(schema)(schema, format_checker=FORMAT_CHECKER)


def validate_updater_json_or_400(submitted_json):
    try:
        get_validator('services-update').validate(submitted_json)
    except ValidationError as e1:
        abort(400, "JSON validation error: {}".format(e1.message))


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
    if validates_against_schema('services-g-cloud-4', submitted_json):
        return 'G-Cloud 4'
    elif validates_against_schema('services-g-cloud-5', submitted_json):
        return 'G-Cloud 5'
    elif (
        validates_against_schema('services-g-cloud-6-scs', submitted_json) or
        validates_against_schema('services-g-cloud-6-saas', submitted_json) or
        validates_against_schema('services-g-cloud-6-paas', submitted_json) or
        validates_against_schema('services-g-cloud-6-iaas', submitted_json)
    ):
        return 'G-Cloud 6'
    elif validates_against_schema('services-g-cloud-7-scs', submitted_json):
        return 'G-Cloud 7'
    else:
        return False


def validate_supplier_json_or_400(submitted_json):
    try:
        get_validator('suppliers').validate(submitted_json)
    except ValidationError as e:
        abort(400, "JSON was not a valid format. {}".format(e.message))


def validate_contact_information_json_or_400(submitted_json):
    try:
        get_validator('contact-information').validate(submitted_json)
    except ValidationError as e:
        abort(400, "JSON was not a valid format. {}".format(e.message))


def validates_against_schema(validator_name, submitted_json):
    try:
        get_validator(validator_name).validate(submitted_json)
    except ValidationError:
        return False
    else:
        return True


def get_validation_errors(validator_name, json_data,
                          enforce_required=True,
                          required_fields=None):
    error_map = {}
    validator = get_validator(validator_name, enforce_required,
                              required_fields)
    errors = validator.iter_errors(json_data)
    form_errors = []
    for error in errors:
        if error.path:
            key = error.path[0]
            error_map[key] = _translate_json_schema_error(error.message)
        elif error.message.endswith("is a required property"):
            key = re.search(r'\'(.*)\'', error.message).group(1)
            error_map[key] = 'answer_required'
        else:
            form_errors.append(error.message)
    if form_errors:
        error_map['_form'] = form_errors
    return error_map


def reason_for_failure(submitted_json):
    response = []
    try:
        get_validator('services-g-cloud-4').validate(submitted_json)
    except ValidationError as e1:
        response.append('Not G4: %s' % e1.message)

    try:
        get_validator('services-g-cloud-5').validate(submitted_json)
    except ValidationError as e1:
        response.append('Not G5: %s' % e1.message)

    try:
        get_validator('services-g-cloud-6-scs').validate(submitted_json)
    except ValidationError as e1:
        response.append('Not SCS: %s' % e1.message)

    try:
        get_validator('services-g-cloud-6-saas').validate(submitted_json)
    except ValidationError as e2:
        response.append('Not SaaS: %s' % e2.message)

    try:
        get_validator('services-g-cloud-6-paas').validate(submitted_json)
    except ValidationError as e3:
        response.append('Not PaaS: %s' % e3.message)

    try:
        get_validator('services-g-cloud-6-iaas').validate(submitted_json)
    except ValidationError as e4:
        response.append('Not IaaS: %s' % e4.message)

    try:
        get_validator('services-g-cloud-7-scs').validate(submitted_json)
    except ValidationError as e5:
        response.append('Not 7-SCS: %s' % e5.message)

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

    return is_valid_string(
        service_id,
        MINIMUM_SERVICE_ID_LENGTH,
        MAXIMUM_SERVICE_ID_LENGTH
    )


def is_valid_service_id_or_400(service_id):
    if is_valid_service_id(service_id):
        return True
    else:
        abort(400, "Invalid service ID supplied: %s" % service_id)


def is_valid_date(date, default_format=DATE_FORMAT):
    try:
        datetime.strptime(date, default_format)
        return True
    except ValueError:
        return False


def is_valid_acknowledged_state(acknowledged):
    return acknowledged in ['all', 'true', 'false']


def is_valid_string_or_400(string):
    if not is_valid_string(string):
        abort(400, "invalid value {}".format(string))


def is_valid_string(string, minlength=1, maxlength=255):
    regex_match_valid_service_id = r"^[A-z0-9-]{%s,%s}$" % (
        minlength,
        maxlength
    )

    if re.search(regex_match_valid_service_id, string):
        return True

    return False


def _translate_json_schema_error(message):
    if message.endswith('is too short'):
        return 'answer_required'
    if message.endswith('is too long'):
        if message.startswith('['):
            # A list that is too long - all our lists are max 10 items
            return 'under_10_items'
        else:
            # A string that is too long
            return 'under_character_limit'
    if 'does not match' in message:
        return 'under_{}_words'.format(_get_word_count(message))
    return message


def _get_word_count(message):
    count_minus_one_string = re.search("\{0,(\d+)", message).group(1)
    count_minus_one = int(count_minus_one_string)
    return count_minus_one + 1
