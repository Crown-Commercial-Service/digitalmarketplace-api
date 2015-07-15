from dmutils.audit import AuditTypes
from flask import jsonify, abort, request, current_app

from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc
from sqlalchemy.types import String

from .. import main
from ... import db
from ...utils import drop_foreign_fields, json_has_required_keys
from ...validation import is_valid_service_id_or_400
from ...models import Service, DraftService, Supplier, AuditEvent, Framework
from ...service_utils import validate_and_return_updater_request, \
    update_and_validate_service, index_service, validate_service, \
    commit_and_archive_service, create_service_from_draft
from ...draft_utils import validate_and_return_draft_request, \
    get_draft_validation_errors


@main.route('/draft-services/copy-from/<string:service_id>', methods=['PUT'])
def copy_draft_service_from_existing_service(service_id):
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

    draft_service = DraftService.query.filter(
        DraftService.service_id == service_id
    ).first()
    if draft_service:
        abort(400, "Draft already exists for service {}".format(service_id))

    draft = DraftService.from_service(service)

    db.session.add(draft)
    db.session.flush()

    audit = AuditEvent(
        audit_type=AuditTypes.create_draft_service,
        user=updater_json['updated_by'],
        data={
            "draftId": draft.id,
            "serviceId": service_id
        },
        db_object=draft
    )
    db.session.add(audit)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(services=draft.serialize()), 201


@main.route('/draft-services/<int:draft_id>', methods=['POST'])
def edit_draft_service(draft_id):
    """
    Edit a draft service
    :param draft_id:
    :return:
    """

    updater_json = validate_and_return_updater_request()
    update_json = validate_and_return_draft_request()
    page_questions = update_json.pop('page_questions', [])
    draft = DraftService.query.filter(
        DraftService.id == draft_id
    ).first_or_404()

    draft.update_from_json(update_json)
    errs = get_draft_validation_errors(draft.data,
                                       draft.data['lot'],
                                       framework_id=draft.framework_id,
                                       required=page_questions)
    if errs:
        abort(400, errs)

    audit = AuditEvent(
        audit_type=AuditTypes.update_draft_service,
        user=updater_json['updated_by'],
        data={
            "draftId": draft_id,
            "serviceId": draft.service_id,
            "updateJson": update_json
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
def list_draft_services():
    supplier_id = request.args.get('supplier_id')
    service_id = request.args.get('service_id')
    framework_slug = request.args.get('framework')
    if supplier_id is None:
        abort(400, "Invalid page argument: supplier_id is required")
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

    if service_id:
        is_valid_service_id_or_400(service_id)
        services = services.filter(DraftService.service_id == service_id)

    if framework_slug:
        framework = Framework.query.filter(
            Framework.slug == framework_slug
        ).first()
        services = services.filter(DraftService.framework_id == framework.id)

    items = services.filter(DraftService.supplier_id == supplier_id).all()
    return jsonify(
        services=[service.serialize() for service in items],
        links=dict()
    )


@main.route('/draft-services/<int:draft_id>', methods=['GET'])
def fetch_draft_service(draft_id):
    """
    Return a draft service
    :param draft_id:
    :return:
    """

    draft = DraftService.query.filter(
        DraftService.id == draft_id
    ).first_or_404()

    return jsonify(services=draft.serialize())


@main.route('/draft-services/<int:draft_id>', methods=['DELETE'])
def delete_draft_service(draft_id):
    """
    Delete a draft service
    :param draft_id:
    :return:
    """

    updater_json = validate_and_return_updater_request()

    draft = DraftService.query.filter(
        DraftService.id == draft_id
    ).first_or_404()

    audit = AuditEvent(
        audit_type=AuditTypes.delete_draft_service,
        user=updater_json['updated_by'],
        data={
            "draftId": draft_id,
            "serviceId": draft.service_id
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


@main.route('/draft-services/<int:draft_id>/publish', methods=['POST'])
def publish_draft_service(draft_id):
    """
    Publish a draft service
    :param draft_id:
    :return:
    """

    update_details = validate_and_return_updater_request()

    draft = DraftService.query.filter(
        DraftService.id == draft_id
    ).first_or_404()

    if draft.service_id:
        service = Service.query.filter(
            Service.service_id == draft.service_id
        ).first_or_404()

        service_from_draft = update_and_validate_service(
            service,
            draft.data)

    else:
        service_from_draft = create_service_from_draft(draft, "enabled")

    commit_and_archive_service(service_from_draft, update_details,
                               AuditTypes.publish_draft_service,
                               audit_data={'draftId': draft_id})

    try:
        db.session.delete(draft)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.warning(
            'Failed to delete draft {} after publishing service {}: {}'.format(
                draft_id, service_from_draft.service_id, e.message)
        )

    index_service(service_from_draft)

    return jsonify(services=service_from_draft.serialize()), 200


@main.route('/draft-services/<string:framework_slug>/create', methods=['POST'])
def create_new_draft_service(framework_slug):
    """
    Create a new draft service with lot, supplier_id, draft_id, framework_id
    :return: the new draft id and location e.g.
    HTTP/1.1 201 Created Location: /draft-services/63636
    """
    updater_json = validate_and_return_updater_request()
    draft_json = validate_and_return_draft_request()
    json_has_required_keys(draft_json, ['lot', 'supplierId'])

    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first()

    if framework.status != 'open':
        abort(400, "'{}' is not open for submissions".format(framework_slug))

    supplier_id = draft_json['supplierId']
    lot = draft_json['lot']
    errs = get_draft_validation_errors(draft_json, lot, slug=framework_slug)
    if errs:
        return jsonify(errors=errs), 400

    draft_json = drop_foreign_fields(draft_json, ['supplierId'])
    draft = DraftService(
        framework_id=framework.id,
        supplier_id=supplier_id,
        data=draft_json,
        status="not-submitted"
    )
    try:
        db.session.add(draft)
        db.session.flush()

        audit = AuditEvent(
            audit_type=AuditTypes.create_draft_service,
            user=updater_json['updated_by'],
            data={
                "draftId": draft.id
            },
            db_object=draft
        )
        db.session.add(audit)

        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    return jsonify(services=draft.serialize()), 201
