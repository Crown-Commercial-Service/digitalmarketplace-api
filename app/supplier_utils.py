from .validation import validate_supplier_json_or_400, validate_new_supplier_json_or_400
from .utils import get_json_from_request, json_has_matching_id, json_has_required_keys, drop_foreign_fields


def validate_and_return_supplier_request(supplier_id=None):
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['suppliers'])
    json_has_required_keys(json_payload['suppliers'], ['contactInformation'])

    # remove unnecessary fields
    json_payload['suppliers'] = drop_foreign_fields(json_payload['suppliers'], ['links'])
    json_payload['suppliers']['contactInformation'] = [
        drop_foreign_fields(contact_data, ['links'])
        for contact_data in json_payload['suppliers']['contactInformation']
    ]

    if supplier_id:
        validate_supplier_json_or_400(json_payload['suppliers'])
        json_has_matching_id(json_payload['suppliers'], supplier_id)
    else:
        validate_new_supplier_json_or_400(json_payload['suppliers'])

    return json_payload['suppliers']
