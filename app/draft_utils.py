from models import Framework
from utils import get_json_from_request, json_has_required_keys, \
    json_has_matching_id
from validation import get_validation_errors


def validate_and_return_draft_request(draft_id=0):
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['services'])
    if draft_id:
        json_has_matching_id(json_payload['services'], draft_id)
    return json_payload['services']


def get_draft_validation_errors(draft_json, framework_id, lot, required=None):
    framework = Framework.query.filter(
        Framework.id == framework_id
    ).first()
    fm_int = framework.name[-1]
    errs = get_validation_errors(
        "services-g{0}-{1}".format(fm_int, lot.lower()),
        draft_json,
        enforce_required=False,
        required_fields=required
    )
    return errs
