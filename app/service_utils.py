from flask import current_app, abort
from sqlalchemy.exc import IntegrityError

from .utils import get_json_from_request, \
    json_has_matching_id, json_has_required_keys, drop_foreign_fields
from .validation import validate_updater_json_or_400, detect_framework_or_400
from . import search_api_client, apiclient
from . import db
from .models import ArchivedService, AuditEvent


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


def update_and_validate_service(service, service_payload):
    service.update_from_json(service_payload)
    validate_service(service)
    return service


def validate_service(service):
    data = service.serialize()
    data = drop_foreign_fields(
        data,
        ['service_id', 'supplierName', 'links', 'frameworkName', 'updatedAt'])
    detect_framework_or_400(data)
    return


def commit_and_archive_service(updated_service, update_details,
                               audit_type, audit_data=None):
    service_to_archive = ArchivedService.from_service(updated_service)

    last_archive = ArchivedService.query.filter(
        ArchivedService.service_id == updated_service.service_id
    ).order_by(ArchivedService.id.desc()).first()

    last_archive = last_archive.id if last_archive else None

    if audit_data is None:
        audit_data = {}

    db.session.add(updated_service)
    db.session.add(service_to_archive)

    try:
        db.session.flush()

        audit_data.update({
            'serviceId': updated_service.service_id,
            'oldArchivedServiceId': last_archive,
            'newArchivedServiceId': service_to_archive.id,
        })

        audit = AuditEvent(
            audit_type=audit_type,
            user=update_details['updated_by'],
            data=audit_data,
            db_object=updated_service,
        )

        db.session.add(audit)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig)


def index_service(service):
    if service.framework.status == 'live' and service.status == 'published':
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
            'Failed to remove {} to search index: {}'.format(
                service.service_id, e.message))
