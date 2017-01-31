from flask import abort
from .validation import validate_supplier_json_or_400, validate_new_supplier_json_or_400, get_validation_errors
from .utils import get_json_from_request, json_has_matching_id, json_has_required_keys, drop_foreign_fields


def validate_and_return_supplier_request():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['suppliers'])
    json_has_required_keys(json_payload['suppliers'], ['contactInformation'])

    # remove unnecessary fields
    json_payload['suppliers'] = drop_foreign_fields(json_payload['suppliers'], ['links'], recurse=True)

    validate_new_supplier_json_or_400(json_payload['suppliers'])

    return json_payload['suppliers']


def validate_agreement_details_data(agreement_details, enforce_required=True, required_fields=None):
    errs = get_validation_errors(
        'agreement-details',
        agreement_details,
        enforce_required=enforce_required,
        required_fields=required_fields
    )

    if errs:
        abort(400, errs)
