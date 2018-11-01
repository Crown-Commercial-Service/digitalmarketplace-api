from operator import itemgetter

from flask import abort, current_app, jsonify, request
from pendulum import Pendulum
from sqlalchemy import asc

from app.utils import get_json_from_request, json_has_required_keys
from dmapiclient.audit import AuditTypes

from .. import main
from ...models import (ArchivedService, AuditEvent, Framework, PriceSchedule,
                       Service, ServiceRole, Supplier, ValidationError, db)
from ...service_utils import (commit_and_archive_service,
                              delete_service_from_index, filter_services,
                              index_service, update_and_validate_service,
                              validate_and_return_related_objects,
                              validate_and_return_service_request,
                              validate_service_data)
from ...utils import (display_list, get_int_or_400, get_valid_page_or_1,
                      pagination_links, url_for,
                      validate_and_return_updater_request)
from ...validation import is_valid_service_id_or_400


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


@main.route('/roles', methods=['GET'])
def list_service_roles():
    roles = ServiceRole.query.all()

    def serialize_with_abbreviations(role):
        return {
            'category': role.category.name,
            'categoryAbbreviation': role.category.abbreviation,
            'role': role.name,
            'roleAbbreviation': role.abbreviation,
        }

    return jsonify(roles=[serialize_with_abbreviations(r) for r in roles])


@main.route('/roles/count', methods=['GET'])
def get_roles_stats():
    top_roles = []
    all_roles = ServiceRole.query.all()

    for role in all_roles:
        name = role.name.replace('Junior', '').replace('Senior', '').strip()
        count = PriceSchedule.query.filter(PriceSchedule.service_role_id == role.id).count()
        dict_exist = False
        for top_role in top_roles:
            if top_role['name'] == name:
                top_role['count'] += count
                dict_exist = True

        if not dict_exist:
            role_data = {
                'name': name,
                'count': count
            }
            top_roles.append(role_data)

    roles = {
        'top_roles': sorted(top_roles, key=itemgetter('count'), reverse=True)
    }

    return jsonify(roles=roles)


@main.route('/services', methods=['GET'])
def list_services():
    page = get_valid_page_or_1()

    supplier_code = get_int_or_400(request.args, 'supplier_code')

    if request.args.get('framework'):
        frameworks = [slug.strip() for slug in request.args['framework'].split(',')]
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

    if supplier_code is not None:
        supplier = Supplier.query.filter(Supplier.code == supplier_code).all()
        if not supplier:
            abort(404, "supplier_code '%d' not found" % supplier_code)

        items = services.default_order().filter(Service.supplier_code == supplier_code).all()
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
