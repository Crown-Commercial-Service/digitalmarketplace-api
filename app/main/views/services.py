from dmapiclient.audit import AuditTypes

from flask import jsonify, abort, request, current_app

from .. import main
from ...models import ArchivedService, Service, Supplier, AuditEvent, Framework

from sqlalchemy import asc
from ...validation import is_valid_service_id_or_400
from ...utils import (
    url_for, pagination_links, display_list, get_valid_page_or_1,
    validate_and_return_updater_request,
)

from ...service_utils import (
    validate_and_return_service_request,
    update_and_validate_service,
    index_service,
    delete_service_from_index,
    commit_and_archive_service,
    validate_service_data,
    validate_and_return_related_objects,
)


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

    supplier_id = request.args.get('supplier_id')

    if request.args.get('framework'):
        services = Service.query.has_frameworks(*[
            slug.strip() for slug in request.args['framework'].split(',')
        ])
    else:
        services = Service.query.framework_is_live()

    if request.args.get('status'):
        services = services.has_statuses(*[
            status.strip() for status in request.args['status'].split(',')
        ])

    if supplier_id is not None:
        try:
            supplier_id = int(supplier_id)
        except ValueError:
            abort(400, "Invalid supplier_id: %s" % supplier_id)

        supplier = Supplier.query.filter(Supplier.supplier_id == supplier_id).all()
        if not supplier:
            abort(404, "supplier_id '%d' not found" % supplier_id)

        items = services.default_order().filter(Service.supplier_id == supplier_id).all()
        return jsonify(
            services=[service.serialize() for service in items],
            links=dict()
        )
    else:
        services = services.order_by(asc(Service.id))

    services = services.paginate(
        page=page,
        per_page=current_app.config['DM_API_SERVICES_PAGE_SIZE'],
    )

    return jsonify(
        services=[service.serialize() for service in services.items],
        links=pagination_links(
            services,
            '.list_services',
            request.args
        )
    )


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
    )


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

    updated_service = update_and_validate_service(service, update)

    commit_and_archive_service(updated_service, update_details,
                               AuditTypes.update_service)
    index_service(updated_service)

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

    return jsonify(services=service.serialize()), 201


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
    )


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

    return jsonify(services=service.serialize())


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
        "disabled"
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

        # If it's being unpublished, delete it from the search api.
        if prior_status == 'published':
            delete_service_from_index(service)
        else:
            # If it's being published, index in the search api.
            index_service(service)

    return jsonify(services=service.serialize()), 200
