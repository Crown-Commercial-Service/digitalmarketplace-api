from collections import MutableSet
from weakref import WeakSet

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
    except BadRequest as e:
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


# based on http://stackoverflow.com/a/16994637
class IdentitySet(MutableSet):
    "A `set` implementation based on object identity rather than equality. Therefore works with non-hashable objects."
    class _Ref(object):
        "A trivial object wrapper which causes __hash__ and __eq__ to be based on the wrapped object's identity"
        def __init__(self, value):
            self.value = value

        def __eq__(self, other):
            return self.value is other.value

        def __hash__(self):
            return id(self.value)

    _internal_set_impl = set

    def __init__(self, iterable=()):
        self.refs = self._internal_set_impl(map(self._Ref, iterable))

    def __contains__(self, elem):
        return self._Ref(elem) in self.refs

    def __iter__(self):
        return (ref.value for ref in self.refs)

    def __len__(self):
        return len(self.refs)

    def add(self, elem):
        return self.refs.add(self._Ref(elem))

    def discard(self, elem):
        return self.refs.discard(self._Ref(elem))

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, list(self))


class WeakIdentitySet(IdentitySet):
    _internal_set_impl = WeakSet
