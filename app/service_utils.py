from flask import current_app
from .utils import get_json_from_request, \
    json_has_matching_id, json_has_required_keys, drop_foreign_fields
from .validation import validate_updater_json_or_400, detect_framework_or_400
from . import search_api_client, apiclient


def validate_and_return_updater_request():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['update_details'])
    validate_updater_json_or_400(json_payload['update_details'])
    return json_payload['update_details']


def validate_and_return_service_request(service_id):
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['services'])
    json_has_matching_id(json_payload['services'], service_id)
    return json_payload['services']


def update_and_validate_service(service, service_payload, updater_payload):
    service.update_from_json(
        service_payload,
        updated_by=updater_payload['updated_by'],
        updated_reason=updater_payload['update_reason'])

    data = service.serialize()

    data = drop_foreign_fields(
        data,
        ['service_id', 'supplierName', 'links', 'frameworkName'])

    detect_framework_or_400(data)
    return service


def index_service(service):
    if not service.framework.expired:
        try:
            search_api_client.index(
                service.service_id,
                service.data,
                service.supplier.name,
                service.framework.name)
        except apiclient.HTTPError as e:
            current_app.logger.warning(
                'Failed to add {} to search index: {}'.format(
                    service.service_id, e.message))


def delete_service_from_index(service):
    try:
        search_api_client.delete(service.service_id)
    except apiclient.HTTPError as e:
        current_app.logger.warning(
            'Failed to add {} to search index: {}'.format(
                service.service_id, e.message))
