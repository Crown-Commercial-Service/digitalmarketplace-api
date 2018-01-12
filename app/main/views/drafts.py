from dmapiclient.audit import AuditTypes
from flask import jsonify, abort, request, current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc

from .. import main
from ... import db, isolation_level
from ...validation import is_valid_service_id_or_400
from ...models import Service, DraftService, Supplier, AuditEvent, Framework
from ...utils import (
    get_int_or_400,
    get_request_page_questions,
    json_only_has_required_keys,
    list_result_response,
    single_result_response,
    validate_and_return_updater_request,
)
from ...service_utils import (
    commit_and_archive_service,
    create_service_from_draft,
    get_service_validation_errors,
    index_service,
    update_and_validate_service,
    validate_and_return_related_objects,
    validate_service_data,
)
from ...draft_utils import validate_and_return_draft_request

RESOURCE_NAME = "services"


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
        DraftService.service_id == service_id,
        DraftService.status.notin_(('not-submitted', 'submitted')),
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
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, draft), 201


@main.route('/draft-services/<int:draft_id>', methods=['POST'])
@isolation_level("SERIALIZABLE")
def edit_draft_service(draft_id):
    """
    Edit a draft service
    :param draft_id:
    :return:
    """

    updater_json = validate_and_return_updater_request()
    update_json = validate_and_return_draft_request()
    page_questions = get_request_page_questions()

    draft = DraftService.query.filter(
        DraftService.id == draft_id
    ).first_or_404()

    draft.update_from_json(update_json)
    validate_service_data(draft, enforce_required=(draft.status == 'submitted'), required_fields=page_questions)

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
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, draft), 200


@main.route('/draft-services', methods=['GET'])
def list_draft_services():
    supplier_id = get_int_or_400(request.args, 'supplier_id')
    service_id = request.args.get('service_id')
    framework_slug = request.args.get('framework')

    if supplier_id is None:
        abort(400, "Invalid page argument: supplier_id is required")

    supplier = Supplier.query.filter(Supplier.supplier_id == supplier_id).all()
    if not supplier:
        abort(404, "supplier_id '{}' not found".format(supplier_id))

    services = DraftService.query.order_by(
        asc(DraftService.id)
    )

    if service_id:
        is_valid_service_id_or_400(service_id)
        services = services.filter(DraftService.service_id == service_id)

    if framework_slug:
        framework = Framework.query.filter(
            Framework.slug == framework_slug
        ).first()
        if not framework:
            abort(404, "framework '{}' not found".format(framework_slug))
        services = services.filter(DraftService.framework_id == framework.id)

    services = services.filter(DraftService.supplier_id == supplier_id)
    return list_result_response(RESOURCE_NAME, services), 200


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

    last_audit_event = AuditEvent.query.last_for_object(draft, [
        AuditTypes.create_draft_service.value,
        AuditTypes.update_draft_service.value,
        AuditTypes.complete_draft_service.value,
    ])

    return jsonify(
        services=draft.serialize(),
        auditEvents=(last_audit_event.serialize(include_user=True) if last_audit_event else None),
        validationErrors=get_service_validation_errors(draft)
    ), 200


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
        abort(400, format(e))

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

    if draft.status == 'not-submitted':
        abort(400, "Cannot publish a draft if it is not submitted: {}".format(draft.status))
    if draft.status == 'submitted' and draft.service_id:
        abort(400, "Cannot re-publish a submitted service")

    if draft.service_id:
        """
        Publishing the draft with a "service_id" updates the original service -- it doesn't create a new one
        This was an alternative editing model proposed by @minglis way way back.
        We're not actually doing this anywhere, but it's tested and it looks like it works.
        """
        service = Service.query.filter(
            Service.service_id == draft.service_id
        ).first_or_404()

        service_from_draft = update_and_validate_service(service, draft.data)
    else:
        service_from_draft = create_service_from_draft(draft, "published")

    commit_and_archive_service(service_from_draft, update_details,
                               AuditTypes.publish_draft_service,
                               audit_data={'draftId': draft_id})

    try:
        if draft.status == 'submitted':
            draft.service_id = service_from_draft.service_id
            db.session.add(draft)
        else:
            db.session.delete(draft)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        action = 'update' if draft.status == 'submitted' else 'delete'
        current_app.logger.warning(
            'Failed to {action} draft {draft_id} after publishing service {service_id}: {error}'.format(
                extra=dict(
                    action=action, draft_id=draft_id, service_id=service_from_draft.service_id, error=e.message)))

    index_service(service_from_draft)

    return single_result_response(RESOURCE_NAME, service_from_draft), 200


@main.route('/draft-services', methods=['POST'])
def create_new_draft_service():
    """
    Create a new draft service with lot, supplier_id, draft_id, framework_id
    :return: the new draft id and location e.g.
    HTTP/1.1 201 Created Location: /draft-services/63636
    """
    updater_json = validate_and_return_updater_request()
    draft_json = validate_and_return_draft_request()
    page_questions = get_request_page_questions()

    framework, lot, supplier = validate_and_return_related_objects(draft_json)

    if framework.status != 'open':
        abort(400, "'{}' is not open for submissions".format(framework.slug))

    if lot.one_service_limit:
        lot_service = DraftService.query.filter(
            DraftService.supplier == supplier,
            DraftService.lot == lot,
            DraftService.framework_id == framework.id
        ).first()
        if lot_service:
            abort(400, "'{}' service already exists for supplier '{}'".format(lot.slug, supplier.supplier_id))

    draft = DraftService(
        framework=framework,
        lot=lot,
        supplier=supplier,
        data=draft_json,
        status="not-submitted"
    )

    validate_service_data(draft, enforce_required=False, required_fields=page_questions)

    try:
        db.session.add(draft)
        db.session.flush()

        audit = AuditEvent(
            audit_type=AuditTypes.create_draft_service,
            user=updater_json['updated_by'],
            data={
                "draftId": draft.id,
                "draftJson": draft_json,
            },
            db_object=draft
        )
        db.session.add(audit)

        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, draft), 201


@main.route('/draft-services/<int:draft_id>/complete', methods=['POST'])
def complete_draft_service(draft_id):
    updater_json = validate_and_return_updater_request()

    draft = DraftService.query.filter(
        DraftService.id == draft_id
    ).first_or_404()

    validate_service_data(draft)

    draft.status = 'submitted'
    try:
        db.session.add(draft)
        db.session.flush()

        audit = AuditEvent(
            audit_type=AuditTypes.complete_draft_service,
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
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, draft), 200


@main.route('/draft-services/<int:draft_id>/update-status', methods=['POST'])
def update_draft_service_status(draft_id):
    updater_json = validate_and_return_updater_request()
    update_json = validate_and_return_draft_request()
    json_only_has_required_keys(update_json, ['status'])

    new_status = update_json['status']
    if not new_status or new_status not in DraftService.STATUSES:
        abort(400, "'{}' is not a valid status".format(new_status))

    draft = DraftService.query.filter(
        DraftService.id == draft_id
    ).first_or_404()

    draft.status = new_status
    try:
        db.session.add(draft)
        db.session.flush()

        audit = AuditEvent(
            audit_type=AuditTypes.update_draft_service_status,
            user=updater_json['updated_by'],
            data={
                "draftId": draft.id,
                "status": new_status
            },
            db_object=draft
        )
        db.session.add(audit)

        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, draft), 200


@main.route('/draft-services/<int:draft_id>/copy', methods=['POST'])
def copy_draft_service(draft_id):
    updater_json = validate_and_return_updater_request()

    original_draft = DraftService.query.filter(
        DraftService.id == draft_id
    ).first_or_404()

    draft_copy = original_draft.copy()

    try:
        db.session.add(draft_copy)
        db.session.flush()

        audit = AuditEvent(
            audit_type=AuditTypes.create_draft_service,
            user=updater_json['updated_by'],
            data={
                "draftId": draft_copy.id,
                "originalDraftId": original_draft.id,
            },
            db_object=draft_copy
        )
        db.session.add(audit)

        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, draft_copy), 201
