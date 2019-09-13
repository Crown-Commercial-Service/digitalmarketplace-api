import random

from flask import url_for as base_url_for
from flask import abort, current_app, request, jsonify
from werkzeug.exceptions import BadRequest

from .validation import validate_updater_json_or_400
from . import search_api_client, dmapiclient


def random_positive_external_id() -> int:
    """
    Generate a random integer ID that's 15-digits long.
    """
    return random.SystemRandom().randint(10 ** 14, (10 ** 15) - 1)


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


def result_meta(total_count):
    return {"total": total_count}


def single_result_response(result_name, result, serialize_kwargs=None):
    """Return a standardised JSON response for a single serialized SQLAlchemy result e.g. a single brief"""
    return jsonify(**{result_name: result.serialize(**(serialize_kwargs if serialize_kwargs else {}))})


def list_result_response(result_name, results_query, serialize_kwargs=None):
    """
    Return a standardised JSON response for a SQLAlchemy result query e.g. a query that will retrieve closed briefs.
    The query should not be executed before being passed in as a argument. Results will be returned in a list and use
    the results `serialize` method for presentation.
    """
    serialized_results = [
        result.serialize(**(serialize_kwargs if serialize_kwargs else {})) for result in results_query
    ]
    meta = result_meta(len(serialized_results))
    return jsonify(meta=meta, **{result_name: serialized_results})


def paginated_result_response(result_name, results_query, page, per_page, endpoint, request_args, serialize_kwargs={}):
    """
    Return a standardised JSON response for a page of serialized results for a SQLAlchemy result query e.g. the third
    page of results for a query that will retrieve closed briefs. The query should not be executed before being passed
    in as a argument so we can manipulate the query object (i.e. to do the pagination). Results will be returned in a
    list and use the results `serialize` method for presentation.
    """
    pagination = results_query.paginate(page=page, per_page=per_page)
    meta = result_meta(pagination.total)
    serialized_results = [
        result.serialize(**(serialize_kwargs if serialize_kwargs else {})) for result in pagination.items
    ]
    links = pagination_links(pagination, endpoint, request_args)
    return jsonify(meta=meta, links=links, **{result_name: serialized_results})


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
        for k, v in json_object.items():
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
    if isinstance(data, str):
        return data.strip()
    elif isinstance(data, dict):
        return {key: strip_whitespace_from_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return list(filter(lambda x: x != '', map(strip_whitespace_from_data, data)))
    else:
        return data


def purge_nulls_from_data(data):
    return dict((k, v) for k, v in data.items() if v is not None)


def get_request_page_questions():
    json_payload = get_json_from_request()
    return json_payload.get('page_questions', [])


def index_object(framework, doc_type, object_id, serialized_object, wait_for_response: bool = True):
    try:
        index_name = current_app.config['DM_FRAMEWORK_TO_ES_INDEX'][framework][doc_type]

        try:
            search_api_client.index(
                index_name=index_name,
                object_id=object_id,
                serialized_object=serialized_object,
                doc_type=doc_type,
                client_wait_for_response=wait_for_response,
            )
        except dmapiclient.HTTPError as e:
            current_app.logger.warning(
                'Failed to add {} object with id {} to {} index: {}'.format(
                    doc_type, object_id, index_name, e.message))

    except KeyError:
        current_app.logger.error(
            "Failed to find index name for framework '{}' with object type '{}'".format(framework, doc_type)
        )
