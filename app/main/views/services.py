from dmapiclient.audit import AuditTypes
from flask import jsonify, abort, request, current_app
from sqlalchemy import asc

from dmutils.config import convert_to_boolean
from dmutils.errors.api import ValidationError

from .. import main
from ...models import ArchivedService, Service, Supplier, AuditEvent, Framework, db
from ...validation import is_valid_service_id_or_400
from ...utils import (
    display_list,
    get_int_or_400,
    get_json_from_request,
    get_valid_page_or_1,
    json_only_has_required_keys,
    list_result_response,
    paginated_result_response,
    pagination_links,
    single_result_response,
    url_for,
    validate_and_return_updater_request,
)
from ...service_utils import (
    commit_and_archive_service,
    delete_service_from_index,
    filter_services,
    index_service,
    update_and_validate_service,
    validate_and_return_related_objects,
    validate_and_return_service_request,
    validate_service_data,
)
from .audits import acknowledge_including_previous

RESOURCE_NAME = "services"


@main.route('/')
def index():
    """Entry point for the API, show the resources that are available."""
    return jsonify(links={
        "audits.list": url_for('.list_audits', _external=True),
        "services.list": url_for('.list_services', _external=True),
        "suppliers.list": url_for('.list_suppliers', _external=True),
        "frameworks.list": url_for('.list_frameworks', _external=True),
    }
    ), 200


@main.route('/services', methods=['GET'])
def list_services():
    page = get_valid_page_or_1()

    supplier_id = get_int_or_400(request.args, 'supplier_id')

    response_headers = {"X-Compression-Safe": "0"}

    if request.args.get('framework'):
        frameworks = [slug.strip() for slug in request.args['framework'].split(',')]
        if not db.session.query(Framework.query.filter(
            Framework.slug.in_(frameworks),
            Framework.has_further_competition.is_(True),
        ).exists()).scalar():
            # we don't have any "further competition" services, so all returned data should be fairly public anyway
            response_headers["X-Compression-Safe"] = "1"
    else:
        frameworks = None

    if request.args.get('status'):
        statuses = [status.strip() for status in request.args['status'].split(',')]
    else:
        statuses = None

    try:
        services = filter_services(
            framework_slugs=frameworks,
            statuses=statuses,
            lot_slug=request.args.get('lot'),
            location=request.args.get('location'),
            role=request.args.get('role')
        )
    except ValidationError as e:
        abort(400, e.message)

    if supplier_id is not None:
        supplier = Supplier.query.filter(Supplier.supplier_id == supplier_id).all()
        if not supplier:
            abort(404, "supplier_id '%d' not found" % supplier_id)

        services = services.default_order().filter(Service.supplier_id == supplier_id)
        return list_result_response(RESOURCE_NAME, services), 200
    else:
        services = services.order_by(asc(Service.id))

    return paginated_result_response(
        result_name=RESOURCE_NAME,
        results_query=services,
        page=page,
        per_page=current_app.config['DM_API_SERVICES_PAGE_SIZE'],
        endpoint='.list_services',
        request_args=request.args
    ), 200, response_headers


@main.route('/archived-services', methods=['GET'])
def list_archived_services_by_service_id():
    """
    Retrieves a list of services from the archived_services table
    for the supplied service_id
    :query_param service_id:
    :return: List[service]
    """

    is_valid_service_id_or_400(request.args.get("service-id", "no service id"))
    service_id = request.args.get("service-id", "no service id")

    page = get_valid_page_or_1()

    services = ArchivedService.query.filter(
        ArchivedService.service_id == service_id
    ).order_by(asc(ArchivedService.id))

    services = services.paginate(
        page=page,
        per_page=current_app.config['DM_API_SERVICES_PAGE_SIZE'],
    )

    if request.args and not services.items:
        abort(404)
    return jsonify(
        services=[service.serialize() for service in services.items],
        links=pagination_links(
            services,
            '.list_services',
            request.args
        )
    ), 200


@main.route('/services/<string:service_id>', methods=['POST'])
def update_service(service_id):
    """
        Update a service. Looks service up in DB, and updates the JSON listing.
    """

    is_valid_service_id_or_400(service_id)

    service = Service.query.filter(
        Service.service_id == service_id
    ).first_or_404()

    update_details = validate_and_return_updater_request()
    update = validate_and_return_service_request(service_id)

    # Check for an update to the copied_to_following_framework flag on the service object
    if 'copiedToFollowingFramework' in update:
        if not isinstance(update['copiedToFollowingFramework'], bool):
            abort(400, "Invalid value for 'copiedToFollowingFramework' supplied")
        service.copied_to_following_framework = update['copiedToFollowingFramework']

    if 'supplierId' in update and int(update['supplierId']) != service.supplier_id:
        audit_type = AuditTypes.update_service_supplier
        if len(update.keys()) > 1:
            abort(400, "Cannot update supplierID and other fields at the same time")
        # Discard any other updates
        update = {
            'supplierId': int(update['supplierId'])
        }
    else:
        audit_type = (
            AuditTypes.update_service_admin if request.args.get('user-role') == 'admin' else AuditTypes.update_service
        )
    updated_service = update_and_validate_service(service, update)

    commit_and_archive_service(updated_service, update_details, audit_type)
    index_service(updated_service, wait_for_response=convert_to_boolean(request.args.get("wait-for-index", "true")))

    return jsonify(message="done"), 200


@main.route('/services/<string:service_id>/revert', methods=['POST'])
def revert_service(service_id):
    """
        Revert a service's `data` to that of a previous, supplied archivedServiceId
    """

    service = Service.query.filter(
        Service.service_id == service_id
    ).first_or_404()

    update_details = validate_and_return_updater_request()
    payload_json = get_json_from_request()
    json_only_has_required_keys(payload_json, ("updated_by", "archivedServiceId",))

    try:
        archived_service = ArchivedService.query.filter(
            ArchivedService.id == int(payload_json["archivedServiceId"])
        ).first()
    except ValueError:
        # presumably failed to interpret `archivedServiceId` as an integer
        archived_service = None
    if not archived_service:
        abort(400, "No such ArchivedService")
    if archived_service.service_id != service_id:
        abort(400, "ArchivedService does not correspond to this service id")

    service.data = archived_service.data.copy()
    validate_service_data(service)

    commit_and_archive_service(
        service,
        update_details,
        AuditTypes.update_service,
        audit_data={
            "fromArchivedServiceId": int(payload_json["archivedServiceId"]),
        },
    )
    index_service(service)

    return jsonify(message="done"), 200


@main.route('/services/<string:service_id>', methods=['PUT'])
def import_service(service_id):
    """Import services from legacy digital marketplace

    This endpoint creates new services where we have an existing ID, it
    should not be used as a model for how we add new services.
    """
    is_valid_service_id_or_400(service_id)

    service = Service.query.filter(
        Service.service_id == service_id
    ).first()

    if service is not None:
        abort(400, "Cannot update service by PUT")

    updater_json = validate_and_return_updater_request()
    service_data = validate_and_return_service_request(service_id)

    framework, lot, supplier = validate_and_return_related_objects(service_data)

    service = Service(
        service_id=service_id,
        supplier=supplier,
        lot=lot,
        framework=framework,
        status=service_data.get('status', 'published'),
        created_at=service_data.get('createdAt'),
        updated_at=service_data.get('updatedAt'),
        data=service_data,
    )

    validate_service_data(service)

    commit_and_archive_service(service, updater_json, AuditTypes.import_service)
    index_service(service)

    return single_result_response(RESOURCE_NAME, service), 201


@main.route('/services/<string:service_id>', methods=['GET'])
def get_service(service_id):
    service = Service.query.filter(
        Service.service_id == service_id
    ).first_or_404()

    service_made_unavailable_audit_event = None
    service_is_unavailable = False
    if service.framework.status == 'expired':
        service_is_unavailable = True
        audit_event_object_reference = Framework.query.filter(
            Framework.id == service.framework.id
        ).first_or_404()
        audit_event_update_type = AuditTypes.framework_update.value
    elif service.status != 'published':
        service_is_unavailable = True
        audit_event_object_reference = service
        audit_event_update_type = AuditTypes.update_service_status.value

    if service_is_unavailable:
        service_made_unavailable_audit_event = AuditEvent.query.last_for_object(
            audit_event_object_reference, [audit_event_update_type]
        )

    if service_made_unavailable_audit_event is not None:
        service_made_unavailable_audit_event = service_made_unavailable_audit_event.serialize()

    return jsonify(
        services=service.serialize(),
        serviceMadeUnavailableAuditEvent=service_made_unavailable_audit_event
    ), 200


@main.route('/archived-services/<int:archived_service_id>', methods=['GET'])
def get_archived_service(archived_service_id):
    """
    Retrieves a service from the archived_service by PK
    :param archived_service_id:
    :return: service
    """

    service = ArchivedService.query.filter(
        ArchivedService.id == archived_service_id
    ).first_or_404()

    return single_result_response(RESOURCE_NAME, service), 200


@main.route(
    '/services/<string:service_id>/status/<string:status>',
    methods=['POST']
)
def update_service_status(service_id, status):
    """
    Updates the status parameter of a service, and archives the old one.
    :param service_id:
    :param status:
    :return: the newly updated service in the response
    """

    # Statuses are defined in the Supplier model
    valid_statuses = [
        "published",
        "enabled",
        "disabled",
        "deleted",
    ]

    is_valid_service_id_or_400(service_id)

    service = Service.query.filter(
        Service.service_id == service_id
    ).first_or_404()

    if status not in valid_statuses:
        valid_statuses_single_quotes = display_list(
            ["\'{}\'".format(vstatus) for vstatus in valid_statuses]
        )
        abort(400, "'{}' is not a valid status. Valid statuses are {}".format(
            status, valid_statuses_single_quotes
        ))

    update_json = validate_and_return_updater_request()

    prior_status, service.status = service.status, status

    commit_and_archive_service(service, update_json,
                               AuditTypes.update_service_status,
                               audit_data={'old_status': prior_status,
                                           'new_status': status})

    if prior_status != status:
        wait_for_response = convert_to_boolean(request.args.get("wait-for-index", "true"))
        if prior_status == 'published':
            # If it's being unpublished, delete it from the search api.
            delete_service_from_index(service, wait_for_response=wait_for_response)
        else:
            # If it's being published, index in the search api.
            index_service(service, wait_for_response=wait_for_response)

    return single_result_response(RESOURCE_NAME, service), 200


@main.route('/services/<service_id>/updates/acknowledge', methods=['POST'])
def acknowledge_update_events(service_id):
    service = Service.query.filter(
        Service.service_id == service_id
    ).first_or_404()

    payload_json = get_json_from_request()
    json_only_has_required_keys(payload_json, ("updated_by", "latestAuditEventId",))
    latest_audit_event_id = payload_json["latestAuditEventId"]

    return acknowledge_including_previous(
        latest_audit_event_id,
        restrict_object_id=service.id,
        restrict_object_type=Service,
        restrict_audit_type="update_service",
    )
