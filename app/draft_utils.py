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


def get_draft_validation_errors(draft_json, lot,
                                framework_id=0, slug=None, required=None):
    if not slug and not framework_id:
        raise Exception('Validation requires either framework_id or slug')
    if not slug:
        # TODO: Get framework slug from Framework table once it exists.
        # framework = Framework.query.filter(
        #     Framework.id == framework_id
        # ).first()
        # slug = framework.slug
        if framework_id == 1:
            slug = "g-cloud-6"
        else:
            slug = "g-cloud-7"
    errs = get_validation_errors(
        "services-{0}-{1}".format(slug, lot.lower()),
        draft_json,
        enforce_required=False,
        required_fields=required
    )
    return errs
