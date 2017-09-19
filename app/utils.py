from flask import url_for as base_url_for
from flask import abort, request
from six import iteritems, string_types
from werkzeug.exceptions import BadRequest

from .validation import validate_updater_json_or_400


def validate_and_return_updater_request():
    json_payload = get_json_from_request()

    if 'update_details' in json_payload:
        json_payload = json_payload['update_details']

    validate_updater_json_or_400(json_payload)

    return {'updated_by': json_payload['updated_by']}


def link(rel, href):
    """Generate a link dict from a rel, href pair."""
    if href is not None:
        return {rel: href}


def url_for(*args, **kwargs):
    kwargs.setdefault('_external', True)
    return base_url_for(*args, **kwargs)


def get_valid_page_or_1():
    try:
        return int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")


def get_int_or_400(data, key):
    value = data.get(key)

    if value is None:
        return value

    try:
        return int(value)
    except ValueError:
        abort(400, "Invalid {}: {}".format(key, value))


def pagination_links(pagination, endpoint, args):
    links = dict()
    links['self'] = url_for(endpoint, **args)
    if pagination.has_prev:
        links['prev'] = url_for(endpoint, **dict(list(args.items()) + [('page', pagination.prev_num)]))
    if pagination.has_next:
        links['next'] = url_for(endpoint, **dict(list(args.items()) + [('page', pagination.next_num)]))
        links['last'] = url_for(endpoint, **dict(list(args.items()) + [('page', pagination.pages)]))
    return links


def get_json_from_request():
    if request.content_type not in ['application/json',
                                    'application/json; charset=UTF-8']:
        abort(400, "Unexpected Content-Type, expecting 'application/json'")
    try:
        data = request.get_json()
    except BadRequest:
        data = None
    if data is None:
        abort(400, "Invalid JSON; must be a valid JSON object")
    return data


def json_has_keys(data, required_keys=None, optional_keys=None):
    data_keys = set(data.keys())

    json_has_required_keys(data, required_keys or [])

    unknown_keys = data_keys - set(optional_keys or []) - set(required_keys or [])
    if unknown_keys:
        abort(400, "Invalid JSON should not have '{}' keys".format("', '".join(unknown_keys)))


def json_has_required_keys(data, keys):
    missing_keys = set(keys) - set(data.keys())
    if missing_keys:
        abort(400, "Invalid JSON must have '{}' keys".format("', '".join(missing_keys)))


def json_only_has_required_keys(data, keys):
    if set(keys) != set(data.keys()):
        abort(400, "Invalid JSON must only have {} keys".format(keys))


def drop_foreign_fields(json_object, list_of_keys, recurse=False):
    """Filter a JSON object down by _removing_ all keys in list_of_keys"""
    json_object = keyfilter_json(json_object, lambda k: k not in list_of_keys, recurse)
    return json_object


def drop_all_other_fields(json_object, list_of_keys, recurse=False):
    """Filter a JSON object down by _keeping_ only keys in list_of_keys"""
    json_object = keyfilter_json(json_object, lambda k: k in list_of_keys, recurse)
    return json_object


def keyfilter_json(json_object, filter_func, recurse=True):
    """
    Filter arbitrary JSON structure by filter_func, recursing into the structure if necessary
    :param json_object:
    :param filter_func: a function to apply to each key found in json_object
    :param recurse: True to look recurse into lists and dicts inside json_object
    :return: a filtered copy of json_object with identical types at each level
    """
    filtered_object = json_object
    if isinstance(json_object, list) and recurse:
        filtered_object = list()
        for item in json_object:
            filtered_object.append(keyfilter_json(item, filter_func))
    elif isinstance(json_object, dict):
        filtered_object = dict()
        for k, v in iteritems(json_object):
            if filter_func(k):
                filtered_object[k] = keyfilter_json(v, filter_func) if recurse else v

    return filtered_object


def json_has_matching_id(data, id):
    if 'id' in data and not id == data['id']:
        abort(400, "id parameter must match id in data")


def display_list(l):
    """Returns a comma-punctuated string for the input list
    with a trailing ('Oxford') comma."""
    length = len(l)
    if length <= 2:
        return " and ".join(l)
    else:
        # oxford comma
        return ", ".join(l[:-1]) + ", and " + l[-1]


def strip_whitespace_from_data(data):
    """Recursively strips whitespace and removes empty items from lists"""
    if isinstance(data, string_types):
        return data.strip()
    elif isinstance(data, dict):
        return {key: strip_whitespace_from_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return list(filter(lambda x: x != '', map(strip_whitespace_from_data, data)))
    else:
        return data


def purge_nulls_from_data(data):
    return dict((k, v) for k, v in iteritems(data) if v is not None)


def get_request_page_questions():
    json_payload = get_json_from_request()
    return json_payload.get('page_questions', [])
