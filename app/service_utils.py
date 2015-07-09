from flask import current_app, abort
from sqlalchemy.exc import IntegrityError

from .utils import get_json_from_request, \
    json_has_matching_id, json_has_required_keys, drop_foreign_fields
from .validation import validate_updater_json_or_400, get_validation_errors
from . import search_api_client, apiclient
from . import db
from .models import ArchivedService, AuditEvent, Framework, Service


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

    framework = Framework.query.filter(
        Framework.id == service.framework_id
    ).first()
    slug = framework.slug

    if slug == 'g-cloud-4':
        validator_name = "services-g-cloud-4"
    elif slug == 'g-cloud-5':
        validator_name = "services-g-cloud-5"
    else:
        validator_name = "services-{0}-{1}".format(
            slug, service.data['lot'].lower())

    data = dict(service.data.items())
    data.update({
        'id': service.service_id,
        'supplierId': service.supplier_id,
        'status': service.status
    })

    data = drop_foreign_fields(
        data,
        ['service_id', 'supplierName', 'links', 'frameworkName', 'updatedAt'])
    errs = get_validation_errors(validator_name, data, enforce_required=True)
    if errs:
        abort(400, errs)
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
            'supplierName': updated_service.supplier.name,
            'supplierId': updated_service.supplier.supplier_id,
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
            search_api_client.index(service.service_id, service.serialize())
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


def create_service_from_draft(draft, status):
    counter = 0
    while True:
        db.session.begin_nested()
        service = Service.create_from_draft(draft, status)
        try:
            validate_service(service)
            db.session.add(service)
            db.session.commit()
            return service
        except IntegrityError:
            current_app.logger.warning(
                "Service ID collision on {}".format(service.service_id))
            counter += 1
            db.session.rollback()
            if counter >= 5:
                raise
