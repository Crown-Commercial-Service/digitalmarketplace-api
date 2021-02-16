from dmapiclient.audit import AuditTypes
from flask import jsonify, abort, request, current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import lazyload
from sqlalchemy import asc, desc

from datetime import datetime

from .. import main
from ... import db
from ...supplier_utils import is_g12_recovery_supplier
from ...validation import is_valid_service_id_or_400
from ...models import Service, DraftService, Supplier, AuditEvent, Framework, Lot
from ...utils import (
    get_int_or_400,
    get_json_from_request,
    get_request_page_questions,
    get_valid_page_or_1,
    json_only_has_required_keys,
    list_result_response,
    paginated_result_response,
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
    json_payload = get_json_from_request()

    target_framework_slug = json_payload.get('targetFramework')
    questions_to_copy = set(json_payload.get('questionsToCopy', []))
    questions_to_exclude = set(json_payload.get('questionsToExclude', []))

    if target_framework_slug:
        if not (questions_to_copy or questions_to_exclude):
            abort(400, "Required data missing: either 'questionsToCopy' or 'questionsToExclude'")
        if questions_to_copy and questions_to_exclude:
            # Can't have both include-only and exclude-only question lists
            abort(400, "Supply either 'questionsToCopy' or 'questionsToExclude', not both")
        if questions_to_copy and not isinstance(questions_to_copy, (set, list, tuple)):
            raise TypeError("'questionsToCopy' must be a list, set or tuple")
        if questions_to_exclude and not isinstance(questions_to_exclude, (set, list, tuple)):
            raise TypeError("'questionsToExclude' must be a list, set or tuple")

    service = Service.query.filter(
        Service.service_id == service_id
    ).first_or_404()

    if target_framework_slug:
        target_framework = Framework.query.filter(
            Framework.slug == target_framework_slug
        ).first_or_404()
        if not target_framework.status == 'open':
            abort(400, "Target framework is not open")
        target_framework_id = target_framework.id
    else:
        target_framework_id = service.framework.id

    draft_service = DraftService.query.filter(
        DraftService.service_id == service_id,
        DraftService.status.notin_(('not-submitted', 'submitted')),
    ).first()

    if draft_service and draft_service.framework.id == target_framework_id:
        abort(400, "Draft already exists for service {}".format(service_id))

    draft = DraftService.from_service(
        service,
        questions_to_copy=questions_to_copy,
        questions_to_exclude=questions_to_exclude,
        target_framework_id=target_framework_id,
    )

    if target_framework_id != service.framework.id:
        # TODO: convert data['copiedFromServiceId'] to a foreign key field on the model, linking the new draft with the
        # source service. That way if the draft is deleted, the relationship to the source service will also be removed.
        service.copied_to_following_framework = True
        draft.data['copiedFromServiceId'] = service_id

    db.session.add(draft, service)
    db.session.flush()

    audit = AuditEvent(
        audit_type=AuditTypes.create_draft_service,
        user=updater_json['updated_by'],
        data={
            "draftId": draft.id,
            "serviceId": service_id,
            "supplierId": draft.supplier_id,
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


@main.route('/draft-services/<framework_slug>/<lot_slug>/copy-published-from-framework', methods=['POST'])
def copy_published_from_framework(framework_slug, lot_slug):
    """
    Copy all published services from a given framework/lot to a different framework's drafts.
    :param framework_slug: The slug for the framework to create the new drafts in.
    :param lot: The slug for the lot to copy services from/create drafts forself.
    :return: The count of created drafts.
    """
    updater_json = validate_and_return_updater_request()
    json_payload = get_json_from_request()

    supplier_id = get_int_or_400(json_payload, 'supplierId')
    source_framework_slug = json_payload.get('sourceFrameworkSlug')
    questions_to_copy = json_payload.get('questionsToCopy', [])
    questions_to_exclude = json_payload.get('questionsToExclude', [])

    if not source_framework_slug:
        abort(400, "Required data missing: 'sourceFrameworkSlug'")
    if not (questions_to_copy or questions_to_exclude):
        abort(400, "Required data missing: either 'questionsToCopy' or 'questionsToExclude'")
    if questions_to_copy and questions_to_exclude:
        # Can't have both include-only and exclude-only question lists
        abort(400, "Supply either 'questionsToCopy' or 'questionsToExclude', not both")
    if questions_to_copy and not isinstance(questions_to_copy, list):
        abort(400, "Data error: 'questionsToCopy' must be a list")
    if questions_to_exclude and not isinstance(questions_to_exclude, list):
        abort(400, "Data error: 'questionsToExclude' must be a list")

    target_framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    if target_framework.status != 'open':
        abort(400, "Target framework is not open")

    source_services = Service.query.filter(
        Service.supplier_id == supplier_id,
        Service.framework.has(
            Framework.slug == source_framework_slug
        ),
        Service.lot.has(
            Lot.slug == lot_slug
        ),
        Service.status == 'published',
        Service.copied_to_following_framework == False,  # NOQA
    ).with_for_update(
        of=Service
    ).order_by(
        # Descending order so created drafts id's are sequential in reverse alphabetical order. Helps with ordering
        # in the frontend (most recent id first).
        desc(Service.data['serviceName'].astext)
    ).all()

    drafts_services = []
    for service in source_services:
        draft = DraftService.from_service(
            service,
            questions_to_copy=questions_to_copy,
            questions_to_exclude=questions_to_exclude,
            target_framework_id=target_framework.id,
        )
        drafts_services.append((draft, service))

        service.copied_to_following_framework = True
        db.session.add(draft, service)

    # Flush so the new drafts are assigned an ID, which is used below in the audit events.
    db.session.flush()

    for draft, service in drafts_services:
        audit = AuditEvent(
            audit_type=AuditTypes.create_draft_service,
            user=updater_json['updated_by'],
            data={
                "draftId": draft.id,
                "serviceId": service.id,
                "supplierId": supplier_id,
            },
            db_object=draft
        )

        db.session.add(audit)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return jsonify({
        RESOURCE_NAME: {
            'draftsCreatedCount': len(drafts_services)
        }
    }), 201


@main.route('/draft-services/<int:draft_id>', methods=['POST'])
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
    ).with_for_update(
        of=DraftService
    ).options(
        lazyload('*')
    ).first_or_404()

    draft.update_from_json(update_json)
    validate_service_data(draft, enforce_required=(draft.status == 'submitted'), required_fields=page_questions)

    audit = AuditEvent(
        audit_type=AuditTypes.update_draft_service,
        user=updater_json['updated_by'],
        data={
            "draftId": draft_id,
            "serviceId": draft.service_id,
            "updateJson": update_json,
            "supplierId": draft.supplier_id,
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
def list_draft_services_by_supplier():
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


@main.route('/draft-services/framework/<string:framework_slug>', methods=['GET'])
def find_draft_services_by_framework(framework_slug):
    # Paginated list view for draft services for a framework iteration
    # Includes options to filter by
    # - status (submitted / not-submitted)
    # - supplier_id (i.e. a paginated version of .list_draft_services_by_supplier above)
    # - lot slug (eg cloud-software)
    page = get_valid_page_or_1()
    status = request.args.get('status')
    supplier_id = get_int_or_400(request.args, 'supplier_id')
    lot_slug = request.args.get('lot')

    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first()
    if not framework:
        abort(404, "Framework '{}' not found".format(framework_slug))

    draft_service_query = DraftService.query.order_by(asc(DraftService.id))
    draft_service_query = draft_service_query.filter(DraftService.framework_id == framework.id)

    if status:
        # Filter by 'submitted', 'not-submitted' only
        if status not in ('submitted', 'not-submitted'):
            abort(400, "Invalid argument: status must be 'submitted' or 'not-submitted'")
        draft_service_query = draft_service_query.filter(DraftService.status == status)

    if supplier_id:
        supplier = Supplier.query.filter(Supplier.supplier_id == supplier_id).all()
        if not supplier:
            abort(404, "Supplier_id '{}' not found".format(supplier_id))
        draft_service_query = draft_service_query.filter(DraftService.supplier_id == supplier_id)

    if lot_slug:
        if not framework.get_lot(lot_slug):
            abort(400, "Invalid argument: lot not recognised")
        draft_service_query = draft_service_query.in_lot(lot_slug)

    pagination_params = request.args.to_dict()
    pagination_params['framework_slug'] = framework_slug

    return paginated_result_response(
        result_name=RESOURCE_NAME,
        results_query=draft_service_query,
        page=page,
        per_page=current_app.config['DM_API_SERVICES_PAGE_SIZE'],
        endpoint='.find_draft_services_by_framework',
        request_args=pagination_params
    ), 200


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
    Delete a draft service and (if applicable) reset the service it was copied from
    :param draft_id:
    :return:
    """

    updater_json = validate_and_return_updater_request()

    draft = DraftService.query.filter(
        DraftService.id == draft_id
    ).first_or_404()

    # Reset the source service - there should be a maximum of 1 copy per source service, as once
    # a service is copied, it's removed from the list of available services to copy from.
    # Resetting the .copied_to_following_framework flag on the source when the copy is deleted allows
    # the user to try again with a fresh copy.
    # TODO: remove this when draft.data['copiedFromServiceId'] is converted to a foreign key field
    source_service, source_service_audit = None, None
    if 'copiedFromServiceId' in draft.data:
        source_service_id = draft.data['copiedFromServiceId']
        source_service = Service.query.filter(
            Service.service_id == source_service_id,
            Service.copied_to_following_framework == True  # noqa
        ).first()
        if source_service:
            source_service.copied_to_following_framework = False
            source_service_audit = AuditEvent(
                audit_type=AuditTypes.update_service,
                user=updater_json['updated_by'],
                data={
                    "serviceId": source_service.service_id,
                    "supplierName": source_service.supplier.name,
                    "supplierId": source_service.supplier_id,
                    "copiedToFollowingFramework": False
                },
                db_object=source_service
            )
            source_service_audit.acknowledged = True
            source_service_audit.acknowledged_by = "api_reset_service_copy"
            source_service_audit.acknowledged_at = datetime.utcnow()

    audit = AuditEvent(
        audit_type=AuditTypes.delete_draft_service,
        user=updater_json['updated_by'],
        data={
            "draftId": draft_id,
            "serviceId": draft.service_id,
            "supplierId": draft.supplier_id,
        },
        db_object=None
    )

    db.session.delete(draft)
    db.session.add(audit)
    if source_service:
        db.session.add(source_service)
        db.session.add(source_service_audit)
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
            f'Failed to {action} draft {draft_id} after publishing service {service_from_draft.service_id}: {e}'
        )
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

    if not (framework.status == 'open' or
            (framework.slug == 'g-cloud-12' and is_g12_recovery_supplier(supplier.supplier_id))):
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
        status="not-submitted",
        lot_one_service_limit=lot.one_service_limit,
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
                "supplierId": draft.supplier_id,
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
                "draftId": draft.id,
                "supplierId": draft.supplier_id,
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
                "status": new_status,
                "supplierId": draft.supplier_id,
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
                "supplierId": draft_copy.supplier_id,
            },
            db_object=draft_copy
        )
        db.session.add(audit)

        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, draft_copy), 201
