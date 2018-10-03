from flask import current_app, abort
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import joinedload

from .utils import get_json_from_request, \
    json_has_matching_id, json_has_required_keys
from .validation import get_validation_errors
from . import search_api_client, dmapiclient
from . import db
from .models import ArchivedService, AuditEvent, Framework, Service, Supplier, ValidationError


def validate_and_return_service_request(service_id):
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['services'])
    json_has_matching_id(json_payload['services'], service_id)
    return json_payload['services']


def validate_and_return_lot(json_payload):
    json_has_required_keys(json_payload, ['frameworkSlug', 'lot'])

    framework = (
        Framework
        .query
        .options(
            joinedload(Framework.lots)
        )
        .filter(
            Framework.slug == json_payload['frameworkSlug']
        )
        .first()
    )

    if not framework:
        abort(400, "Framework '{}' does not exist".format(json_payload['frameworkSlug']))

    lot = framework.get_lot(json_payload['lot'])

    if not lot:
        abort(400, "Incorrect lot '{}' for framework '{}'".format(json_payload['lot'], framework.slug))

    return framework, lot


def validate_and_return_supplier(json_payload):
    json_has_required_keys(json_payload, ['supplierCode'])
    try:
        supplier = Supplier.query.filter(
            Supplier.code == json_payload['supplierCode']
        ).first()
    except DataError:
        supplier = None

    if not supplier:
        abort(400, "Invalid supplier Code '{}'".format(json_payload['supplierCode']))

    return supplier


def validate_and_return_related_objects(service_json):
    json_has_required_keys(service_json, ['frameworkSlug', 'lot', 'supplierCode'])

    framework, lot = validate_and_return_lot(service_json)
    supplier = validate_and_return_supplier(service_json)

    return framework, lot, supplier


def update_and_validate_service(service, service_payload):
    service.update_from_json(service_payload)
    validate_service_data(service)
    return service


def _get_validator_name(service):
    if service.framework.slug in ['g-cloud-4', 'g-cloud-5']:
        return 'services-{}'.format(service.framework.slug)
    else:
        return 'services-{}-{}'.format(service.framework.slug, service.lot.slug)


def validate_service_data(service, enforce_required=True, required_fields=None):
    errs = get_service_validation_errors(
        service, enforce_required, required_fields)

    if errs:
        abort(400, errs)


def get_service_validation_errors(service, enforce_required=True, required_fields=None):
    return get_validation_errors(
        _get_validator_name(service), service.data,
        enforce_required=enforce_required,
        required_fields=required_fields
    )


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
            'supplierCode': updated_service.supplier.code,
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
    if (
        service.framework.status == 'live' and
        service.framework.framework == 'g-cloud' and
        service.status == 'published'
    ):
        try:
            search_api_client.index(service.service_id, service.serialize())
        except dmapiclient.HTTPError as e:
            current_app.logger.warning(
                'Failed to add {} to search index: {}'.format(
                    service.service_id, e.message))


def delete_service_from_index(service):
    try:
        search_api_client.delete(service.service_id)
    except dmapiclient.HTTPError as e:
        current_app.logger.warning(
            'Failed to remove {} to search index: {}'.format(
                service.service_id, e.message))


def create_service_from_draft(draft, status):
    counter = 0
    while True:
        db.session.begin_nested()
        service = Service.create_from_draft(draft, status)
        try:
            validate_service_data(service)
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


def filter_services(framework_slugs=None, statuses=None, lot_slug=None, location=None, role=None):
    if framework_slugs:
        services = Service.query.has_frameworks(*framework_slugs)
    else:
        services = Service.query.framework_is_live()

    if statuses:
        services = services.has_statuses(*statuses)

    location_key = "locations"

    if role:
        if lot_slug != 'digital-specialists':
            raise ValidationError("Role only applies to Digital Specialists lot")
        location_key = role + "Locations"
        services = services.data_has_key(location_key)

    if location:
        if not lot_slug:
            raise ValidationError("Lot must be specified to filter by location")
        if lot_slug == 'digital-specialists':
            if not role:
                raise ValidationError("Role must be specified for Digital Specialists")
        services = services.data_key_contains_value(location_key, location)

    if lot_slug:
        services = services.in_lot(lot_slug)

    return services
