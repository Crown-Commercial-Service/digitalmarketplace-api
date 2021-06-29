import json
import re
import os
import copy
from decimal import Decimal
from typing import Iterable, Optional, TYPE_CHECKING

from flask import abort, current_app
import glob
from jsonschema import ValidationError, FormatChecker
from jsonschema.validators import validator_for
from datetime import datetime
from dmutils.formats import DATE_FORMAT

# avoid cyclic imports when not type checking
if TYPE_CHECKING:
    from app.models.buyer_domains import BuyerEmailDomain  # noqa

MINIMUM_SERVICE_ID_LENGTH = 10
MAXIMUM_SERVICE_ID_LENGTH = 20

SCHEMA_PATHS = glob.glob('./json_schemas/*.json')
FORMAT_CHECKER = FormatChecker()


def load_schemas(schema_paths):
    loaded_schemas = {}
    for schema_path in schema_paths:
        schema_name = os.path.splitext(os.path.basename(schema_path))[0]

        with open(schema_path) as f:
            schema = json.load(f)
            validator = validator_for(schema)
            validator.check_schema(schema)
            loaded_schemas[schema_name] = schema
    return loaded_schemas


_SCHEMAS = load_schemas(SCHEMA_PATHS)


def get_validator(schema_name, enforce_required=True, required_fields=None):
    if required_fields is None:
        required_fields = []
    if enforce_required:
        schema = _SCHEMAS[schema_name]
    else:
        schema = copy.deepcopy(_SCHEMAS[schema_name])
        schema['required'] = [
            field for field in schema.get('required', [])
            if field in required_fields
        ]
        schema['dependencies'] = {
            k: v
            for k, v in schema.get('dependencies', {}).items()
            if k in required_fields
        }
        schema.pop('anyOf', None)
    return validator_for(schema)(schema, format_checker=FORMAT_CHECKER)


def validate_updater_json_or_400(submitted_json):
    try:
        get_validator('services-update').validate(submitted_json)
    except ValidationError as e1:
        abort(400, "JSON validation error: {}".format(e1.message))


def validate_user_json_or_400(submitted_json):
    try:
        get_validator('users').validate(submitted_json)
    except ValidationError as e:
        abort(400, "JSON was not a valid format. {}".format(e.message))
    if submitted_json['role'] == 'supplier' \
            and 'supplierId' not in submitted_json:
        abort(400, "No supplier id provided for supplier user")


def validate_user_auth_json_or_400(submitted_json):
    try:
        validates_against_schema('users-auth', submitted_json)
    except ValidationError as e:
        abort(400, "JSON was not a valid format. {}".format(e.message))


def validate_supplier_json_or_400(submitted_json):
    try:
        get_validator('suppliers').validate(submitted_json)
    except ValidationError as e:
        abort(400, "JSON was not a valid format. {}".format(e.message))


def validate_outcome_json_or_400(submitted_json):
    try:
        get_validator('outcome-update').validate(submitted_json)
    except ValidationError as e:
        abort(400, "JSON was not a valid format. {}".format(e.message))


def validate_direct_award_project_json_or_400(submitted_json):
    try:
        get_validator('direct-award-project-update').validate(submitted_json)
    except ValidationError as e:
        abort(400, "JSON was not a valid format. {}".format(e.message))


def validate_new_supplier_json_or_400(submitted_json):
    try:
        get_validator('new-supplier').validate(submitted_json)
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
    validator = get_validator(validator_name, enforce_required,
                              required_fields)
    errors = validator.iter_errors(json_data)

    return translate_json_schema_errors(errors, json_data)


def translate_json_schema_errors(errors, json_data):
    error_map = {}
    form_errors = []
    for error in errors:
        if error.validator == 'oneOf' and error.path:
            if len(error.path) == 1:
                key = error.path[0]
                error_map[key] = _translate_json_schema_error(
                    key, error.validator, error.validator_value, error.message
                )
            else:
                # validate follow-up questions are answered: eg evidence given for a 'yes' nice-to-have
                key, index = error.path
                if key not in error_map:
                    error_map[key] = []
                # figure out which field has failed
                required_contexts = [e for e in error.context if e.validator == 'required']
                if required_contexts:
                    field = re.search(r"'(.*)'", required_contexts[0].message).group(1)

                    error_map[key].append({
                        'field': field,
                        'index': index,
                        'error': 'answer_required'
                    })
                elif type(error_map[key]) is list:
                    # It is possible that error_map[key] is a single error message string. This may happen if you
                    # send a boolean instead of a dictionary as an item of a dynamic list. In this case, we no longer
                    # wish to append errors (also avoiding an attribute error if we attempted to appending to a
                    # string) so will do nothing for this iteration of error in errors. In the end, this function
                    # would return the string error message.
                    error_map[key].append({
                        'index': index,
                        'error': error.message
                    })

        elif error.validator == 'oneOf':
            required_contexts = [e for e in error.context if e.validator == 'required']
            if required_contexts:
                field = re.search(r"'(.*)'", required_contexts[0].message).group(1)
                error_map[field] = 'answer_required'
            else:
                form_errors.append(error.message)

        # validate fields two deep that have required properties e.g. no evidence given for essentialRequirements[1]
        elif error.path and len(error.path) == 2 and error.validator == 'required':
            key, index = error.path
            if key not in error_map:
                error_map[key] = []

            field = re.search(r"'(.*)'", error.message).group(1)

            error_map[key].append({
                'field': field,
                'index': index,
                'error': 'answer_required'
            })

        # validate dynamic list questions that are 3 elements deep, e.g. essentialRequirements[1]['evidence']
        elif error.path and len(error.path) == 3:
            key, index, field = error.path
            if key not in error_map:
                error_map[key] = []

            error_message = _translate_json_schema_error(
                key, error.validator, error.validator_value, error.message
            )

            error_map[key].append({
                'field': field,
                'index': index,
                'error': error_message
            })

        elif error.path:
            key = error.path[0]
            error_map[key] = _translate_json_schema_error(
                key, error.validator, error.validator_value, error.message
            )
        # validate multiquestion dependencies: eg for specialist roles check that all fields are present or none are
        elif error.validator in ['required', 'dependencies']:
            regex = r'u?\'(\w+)\' is a dependency of u?\'(\w+)\'' if error.validator == 'dependencies' else r'\'(.*)\''
            key = re.search(regex, error.message).group(1)
            error_map[key] = 'answer_required'
        # validate at least one item exists: eg specialist/outcome exists when submitting a dos service
        elif error.validator == 'anyOf':
            if error.validator_value[0].get('title'):
                form_errors.append('{}_required'.format(error.validator_value[0].get('title')))
        else:
            form_errors.append(error.message)
    if form_errors:
        error_map['_form'] = form_errors
    error_map.update(min_price_less_than_max_price(error_map, json_data))

    return error_map


def min_price_less_than_max_price(error_map, json_data):
    price_errors = {}
    for key in json_data.keys():
        if key.lower().endswith('pricemin'):
            prefix = key[:-8]
            max_price_key = (prefix + 'PriceMax') if prefix else 'priceMax'
            if (
                json_data.get(max_price_key, None) and
                key not in error_map and
                max_price_key not in error_map
            ):
                if Decimal(json_data[key]) > Decimal(json_data[max_price_key]):
                    price_errors[max_price_key] = 'max_less_than_min'

    return price_errors


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


def _translate_json_schema_error(key, validator, validator_value, message):
    validator_type_to_error = {
        'minLength': 'answer_required',
        'minItems': 'answer_required',
        'minimum': 'not_a_number',
        'exclusiveMaximum': 'not_a_number',
        'maximum': 'not_a_number',
        'maxItems': 'max_items_limit',
        'maxLength': 'under_character_limit',
        'format': 'invalid_format',
    }
    if validator in validator_type_to_error:
        return validator_type_to_error[validator]

    elif validator == 'required':
        if "'assurance'" in message:
            return 'assurance_required'
        else:
            return 'answer_required'

    elif validator == 'pattern':
        # Since error messages are now specified in the manifests, we can (in the future) generalise the returned
        # string and just show the correct message
        if key.endswith(('dayRate', 'priceMin', 'priceMax', 'PriceMin', 'PriceMax', 'awardedContractValue')):
            return 'not_money_format'

        return 'under_{}_words'.format(_get_word_count(validator_value))

    elif validator == 'enum' and validator_value == [True]:
        # Boolean questions where 'yes' is a mandatory answer, e.g. essentialRequirementsMet
        return 'not_required_value'

    elif validator == 'enum' and key == 'priceUnit':
        return 'no_unit_specified'

    elif validator == 'type' and validator_value in ['number', 'integer']:
        return 'not_a_number'

    elif validator == 'type' and validator_value == 'boolean':
        return 'answer_required'

    elif (validator == 'oneOf' and
          type(validator_value) == list
          and validator_value[0].get('type') == 'integer'):
        return 'not_a_number'

    return message


def _get_word_count(message):
    count_minus_one_string = re.search(r"\{0,(\d+)", message).group(1)
    count_minus_one = int(count_minus_one_string)
    return count_minus_one + 1


def validate_buyer_email_domain_json_or_400(submitted_json):
    try:
        get_validator('buyer-email-domains').validate(submitted_json)
    except ValidationError as e1:
        abort(400, "JSON was not a valid format: {}".format(e1.message))


def buyer_email_address_first_approved_domain(
    existing_buyer_domains: Iterable["BuyerEmailDomain"],
    email_address: str,
) -> Optional["BuyerEmailDomain"]:
    """
    Returns the first-matched `BuyerEmailDomain` from `existing_buyer_domains` that qualifies `email_address` for a
    buyer account, or None if there is no such match.
    """
    new_domain = email_address.split('@')[-1]
    return first_approved_buyer_domain(existing_buyer_domains, new_domain)


def first_approved_buyer_domain(
    existing_buyer_domains: Iterable["BuyerEmailDomain"],
    new_domain: str,
) -> Optional["BuyerEmailDomain"]:
    """
    Returns the first-matched `BuyerEmailDomain` from `existing_buyer_domains` that qualifies `new_domain` for a
    buyer account, or None if there is no such match.
    """
    return next(
        (bd for bd in existing_buyer_domains if ("." + new_domain).endswith('.' + bd.domain_name)),
        None,
    )


def buyer_email_address_has_approved_domain(
    existing_buyer_domains: Iterable["BuyerEmailDomain"],
    email_address: str,
) -> bool:
    """
    Check the buyer's email address is from an approved domain
    """
    return buyer_email_address_first_approved_domain(existing_buyer_domains, email_address) is not None


def is_approved_buyer_domain(
    existing_buyer_domains: Iterable["BuyerEmailDomain"],
    new_domain: str,
) -> bool:
    """
    Validate if a domain is approved before an admin adds a new one.
    """
    return first_approved_buyer_domain(existing_buyer_domains, new_domain) is not None


def admin_email_address_has_approved_domain(email_address):
    """
    Check the admin's email address is from a whitelisted domain
    :param email_address: string
    :return: boolean
    """
    return email_address.split('@')[-1] in current_app.config.get('DM_ALLOWED_ADMIN_DOMAINS', [])


def is_valid_email_address(email_address: str) -> bool:
    "Check the email address is valid"
    # regex from Mozilla Developer Network
    # https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/email#Validation
    pattern = r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"  # noqa: E501
    return bool(re.fullmatch(pattern, email_address))
