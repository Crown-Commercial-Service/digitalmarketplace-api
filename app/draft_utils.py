from .utils import get_json_from_request, json_has_required_keys, \
    json_has_matching_id


def validate_and_return_draft_request(draft_id=0):
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['services'])
    if draft_id:
        json_has_matching_id(json_payload['services'], draft_id)
    return json_payload['services']


def get_copiable_service_data(service, questions_to_exclude=None, questions_to_copy=None):
    """
    Filter out any service data that shouldn't be copied to a new draft service, by either including
    copyable questions or excluding non-copyable questions.
    There is validation at view-level to prevent both `to_copy` and `to_exclude` lists being supplied, so
    this function should only receive one or the other. However we want to deprecate use of `to_copy`, so
    if both are somehow supplied, we use the `to_exclude` list.
    If neither list is provided, then all data fields on the service are included.

    :param service: service object with a JSON dict `data` attribute (required)
    :param questions_to_exclude: iterable of question IDs that must not be copied
    :param questions_to_copy: iterable of question IDs that may be copied (to be deprecated)
    :return: JSON dict of service data
    """
    if questions_to_exclude:
        return {key: value for key, value in service.data.items() if key not in questions_to_exclude}
    if questions_to_copy:
        return {key: value for key, value in service.data.items() if key in questions_to_copy}
    return service.data
