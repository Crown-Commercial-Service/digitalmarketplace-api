import pendulum
from flask import url_for as base_url_for
from flask import abort, request
from six import iteritems, string_types
from werkzeug.exceptions import BadRequest

from .validation import validate_updater_json_or_400


from .logs import get_logger, load_config

log = get_logger('api')
load_config()


def sorted_uniques(sequence):
    return list(sorted(set(sequence)))


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


def get_positive_int_or_400(data, key, default=None):
    try:
        value = int(data.get(key, default))
        if value <= 0:
            raise ValueError(value)
    except ValueError as e:
        abort(400, "Invalid {} value (must be integer > 0): {}".format(key, e))
    return value


def get_nonnegative_int_or_400(data, key, default=None):
    try:
        value = int(data.get(key, default))
        if value < 0:
            raise ValueError(value)
    except ValueError as e:
        abort(400, "Invalid {} value (must be integer >= 0): {}".format(key, e))
    return value


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
                                    'application/json; charset=UTF-8',
                                    'application/json; charset=utf-8']:
        abort(400, "Unexpected Content-Type, expecting 'application/json'")
    try:
        data = request.get_json()
    except BadRequest:
        data = None
    if data is None:
        abort(400, "Invalid JSON; must be a valid JSON object")
    return data


def json_has_required_keys(data, keys):
    missing_keys = set(keys) - set(data.keys())
    if missing_keys:
        abort(400, "Invalid JSON must have '%s' keys" % list(missing_keys))


def json_only_has_required_keys(data, keys):
    if set(keys) != set(data.keys()):
        abort(400, "Invalid JSON must only have {} keys".format(keys))


def drop_foreign_fields(json_object, list_of_keys):
    json_object = json_object.copy()
    for key in list_of_keys:
        json_object.pop(key, None)

    return json_object


def filter_fields(dictionary, list_of_keys):
    key_set = set(list_of_keys)
    return {k: v for k, v in dictionary.items() if k in key_set}


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
    for key, value in data.items():
        if isinstance(value, list):
            # Strip whitespace and remove empty items from lists
            data[key] = list(
                filter(lambda x: x != '',
                       map(lambda x: x.strip() if isinstance(x, string_types) else x, value))
            )
        elif isinstance(value, string_types):
            # Strip whitespace from strings
            data[key] = value.strip()
    return data


def purge_nulls_from_data(data):
    return dict((k, v) for k, v in iteritems(data) if v is not None)


def get_request_page_questions():
    json_payload = get_json_from_request()
    return json_payload.get('page_questions', [])


def format_date(date):
    dt = pendulum.parse(str(date))
    return dt.format('DD/MM/YYYY', formatter='alternative')


def format_price(price):
    if price is None:
        return None

    return '{:1,.2f}'.format(price)
