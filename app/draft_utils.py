from .utils import get_json_from_request, json_has_required_keys, \
    json_has_matching_id
from .validation import get_validation_errors


def validate_and_return_draft_request(draft_id=0):
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['services'])
    if draft_id:
        json_has_matching_id(json_payload['services'], draft_id)
    return json_payload['services']


def get_request_page_questions():
    json_payload = get_json_from_request()
    return json_payload.get('page_questions', [])


def get_draft_validation_errors(draft_json, framework=None, lot=None, required=None):
    errs = get_validation_errors(
        "services-{0}-{1}".format(framework.slug, lot.slug),
        draft_json,
        enforce_required=False,
        required_fields=required
    )
    return errs


def validate_draft(draft):
    validator_name = 'services-{}-{}'.format(draft.framework.slug, draft.lot.slug)

    data = dict(draft.data.items())
    data.update({
        'supplierId': draft.supplier_id,
        'status': draft.status
    })

    errs = get_validation_errors(
        validator_name,
        data,
        enforce_required=True
    )

    # Drafts are valid even without the required service ID
    errs.pop('id', None)

    return errs
