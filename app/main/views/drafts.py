from dmutils.audit import AuditTypes
from flask import jsonify, abort, request

from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc
from sqlalchemy.types import String

from .. import main
from ... import db
from ...validation import is_valid_service_id_or_400
from ...models import Service, DraftService, ArchivedService, \
    Supplier, AuditEvent
from ...service_utils import validate_and_return_updater_request, \
    update_and_validate_service, validate_and_return_service_request, \
    index_service


@main.route('/services/<string:service_id>/draft', methods=['PUT'])
def create_draft_service(service_id):
    """
    Create a draft service from an existing service
    :param service_id:
    :return:
    """
    is_valid_service_id_or_400(service_id)
    updater_json = validate_and_return_updater_request()

    service = Service.query.filter(
        Service.service_id == service_id
    ).first_or_404()

    draft = DraftService.from_service(service)
    audit = AuditEvent(
        audit_type=AuditTypes.create_draft_service,
        user=updater_json['updated_by'],
        data={
            "service_id": service_id
        },
        db_object=service
    )

    db.session.add(draft)
    db.session.add(audit)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(services=draft.serialize()), 201


@main.route('/services/<string:service_id>/draft', methods=['POST'])
def edit_draft_service(service_id):
    """
    Edit a draft service
    :param service_id:
    :return:
    """

    is_valid_service_id_or_400(service_id)

    updater_json = validate_and_return_updater_request()
    update_json = validate_and_return_service_request(service_id)

    draft = DraftService.query.filter(
        DraftService.service_id == service_id
    ).first_or_404()

    draft.update_from_json(update_json)

    audit = AuditEvent(
        audit_type=AuditTypes.update_draft_service,
        user=updater_json['updated_by'],
        data={
            "service_id": service_id,
            "update_json": update_json
        },
        db_object=draft
    )

    db.session.add(draft)
    db.session.add(audit)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(services=draft.serialize()), 200


@main.route('/draft-services', methods=['GET'])
def list_drafts():
    supplier_id = request.args.get('supplier_id')
    if supplier_id is None:
        abort(400, "Invalid page argument")
    try:
        supplier_id = int(supplier_id)
    except ValueError:
        abort(400, "Invalid supplier_id: %s" % supplier_id)

    supplier = Supplier.query.filter(Supplier.supplier_id == supplier_id) \
        .all()
    if not supplier:
        abort(404, "supplier_id '%d' not found" % supplier_id)

    services = DraftService.query.order_by(
        asc(DraftService.framework_id),
        asc(DraftService.data['lot'].cast(String).label('data_lot')),
        asc(DraftService.data['serviceName'].
            cast(String).label('data_servicename'))
    )

    items = services.filter(DraftService.supplier_id == supplier_id).all()
    return jsonify(
        services=[service.serialize() for service in items],
        links=dict()
    )


@main.route('/services/<string:service_id>/draft', methods=['GET'])
def fetch_draft_service(service_id):
    """
    Return a draft service
    :param service_id:
    :return:
    """

    is_valid_service_id_or_400(service_id)

    draft = DraftService.query.filter(
        DraftService.service_id == service_id
    ).first_or_404()

    return jsonify(services=draft.serialize())


@main.route('/services/<string:service_id>/draft', methods=['DELETE'])
def delete_draft_service(service_id):
    """
    Delete a draft service
    :param service_id:
    :return:
    """

    is_valid_service_id_or_400(service_id)

    updater_json = validate_and_return_updater_request()

    draft = DraftService.query.filter(
        DraftService.service_id == service_id
    ).first_or_404()

    audit = AuditEvent(
        audit_type=AuditTypes.delete_draft_service,
        user=updater_json['updated_by'],
        data={
            "service_id": service_id
        },
        db_object=None
    )

    db.session.delete(draft)
    db.session.add(audit)
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(message="done"), 200


@main.route('/services/<string:service_id>/draft/publish', methods=['POST'])
def publish_draft_service(service_id):
    """
    Publish a draft service
    :param service_id:
    :return:
    """

    is_valid_service_id_or_400(service_id)

    updater_json = validate_and_return_updater_request()

    draft = DraftService.query.filter(
        DraftService.service_id == service_id
    ).first_or_404()

    service = Service.query.filter(
        Service.service_id == draft.service_id
    ).first_or_404()

    archived_service = ArchivedService.from_service(service)
    new_service = update_and_validate_service(
        service,
        draft.data,
        updater_json)

    audit = AuditEvent(
        audit_type=AuditTypes.publish_draft_service,
        user=updater_json['updated_by'],
        data={
            "service_id": service_id
        },
        db_object=new_service
    )

    db.session.add(audit)
    db.session.add(archived_service)
    db.session.add(new_service)
    db.session.delete(draft)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    index_service(new_service)

    return jsonify(services=new_service.serialize()), 200
