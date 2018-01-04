from flask import abort
from .validation import validate_supplier_json_or_400, validate_new_supplier_json_or_400, get_validation_errors
from .utils import get_json_from_request, json_has_matching_id, json_has_required_keys, drop_foreign_fields


def validate_and_return_supplier_request(supplier_id=None):
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['suppliers'])
    json_has_required_keys(json_payload['suppliers'], ['contactInformation'])

    # remove unnecessary fields
    json_payload['suppliers'] = drop_foreign_fields(json_payload['suppliers'], ['links'], recurse=True)

    if supplier_id:
        validate_supplier_json_or_400(json_payload['suppliers'])
        json_has_matching_id(json_payload['suppliers'], supplier_id)
    else:
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


def check_supplier_role(role, supplier_id):
    if role == 'supplier' and not supplier_id:
        abort(400, "'supplierId' is required for users with 'supplier' role")
    elif role != 'supplier' and supplier_id:
        abort(400, "'supplierId' is only valid for users with 'supplier' role, not '{}'".format(role))
