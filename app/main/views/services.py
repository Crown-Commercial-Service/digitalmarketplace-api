from datetime import datetime

from flask import jsonify, abort, request, current_app

from .. import main
from ... import db
from ... import search_api_client
from ...models import ArchivedService, Service, Supplier, Framework

from sqlalchemy import asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import false
from ...validation import detect_framework_or_400, \
    validate_updater_json_or_400, is_valid_service_id_or_400
from ...utils import url_for, pagination_links, drop_foreign_fields, \
    json_has_matching_id, get_json_from_request, json_has_required_keys, \
    display_list
from sqlalchemy.types import String

from dmutils import apiclient


@main.route('/')
def index():
    """Entry point for the API, show the resources that are available."""
    return jsonify(links={
        "services.list": url_for('.list_services', _external=True),
        "suppliers.list": url_for('.list_suppliers', _external=True)
        }
    ), 200


@main.route('/services', methods=['GET'])
def list_services():
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")

    supplier_id = request.args.get('supplier_id')

    services = Service.query.filter(
        Service.framework.has(Framework.expired == false())
    ).order_by(
        asc(Service.framework_id),
        asc(Service.data['lot'].cast(String).label('data_lot')),
        asc(Service.data['serviceName'].cast(String).label('data_servicename'))
    )

    if request.args.get('status'):
        services = Service.query.filter(
            Service.status.in_(request.values.getlist('status'))
        )

    if supplier_id is not None:
        try:
            supplier_id = int(supplier_id)
        except ValueError:
            abort(400, "Invalid supplier_id: %s" % supplier_id)

        supplier = Supplier.query.filter(Supplier.supplier_id == supplier_id) \
            .all()
        if not supplier:
            abort(404, "supplier_id '%d' not found" % supplier_id)

        services = services.filter(Service.supplier_id == supplier_id)

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

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")

    services = ArchivedService.query.filter(Service.service_id == service_id)

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

    service_to_archive = ArchivedService.from_service(service)

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload,
                           ['services', 'update_details'])

    update_json = json_payload['update_details']
    validate_updater_json_or_400(update_json)

    json_has_matching_id(json_payload['services'], service_id)

    service.update_from_json(json_payload['services'],
                             updated_by=update_json['updated_by'],
                             updated_reason=update_json['update_reason'])

    data = service.serialize()
    data = drop_foreign_fields(data,
                               ['supplierName', 'links', 'frameworkName'])
    detect_framework_or_400(data)

    db.session.add(service)
    db.session.add(service_to_archive)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig)

    if not service.framework.expired:
        try:
            search_api_client.index(
                service_id,
                service.data,
                service.supplier.name,
                service.framework.name)
        except apiclient.HTTPError as e:
            current_app.logger.warning(
                'Failed to add {} to search index: {}'.format(
                    service_id, e.message))

    return jsonify(message="done"), 200


@main.route('/services/<string:service_id>', methods=['PUT'])
def import_service(service_id):
    """Import services from legacy digital marketplace

    This endpoint creates new services where we have an existing ID, it
    should not be used as a model for how we add new services.
    """
    is_valid_service_id_or_400(service_id)

    now = datetime.now()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload,
                           ['services', 'update_details'])

    update_json = json_payload['update_details']
    validate_updater_json_or_400(update_json)

    json_has_matching_id(json_payload['services'], service_id)
    service_data = drop_foreign_fields(
        json_payload['services'],
        ['supplierName', 'links', 'frameworkName']
    )

    framework = detect_framework_or_400(service_data)
    service_data = drop_foreign_fields(service_data, ['id'])

    service = Service.query.filter(
        Service.service_id == service_id
    ).first()

    if service is not None:
        abort(400, "Cannot update service by PUT")

    supplier_id = service_data.pop('supplierId')
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first()
    if supplier is None:
        abort(400, "Key (supplierId)=({}) is not present".format(supplier_id))

    framework = Framework.query.filter(
        Framework.name == framework
    ).first()

    service = Service(service_id=service_id)
    service.supplier_id = supplier.supplier_id
    service.framework_id = framework.id
    service.updated_at = now
    service.created_at = now
    service.status = service_data.pop('status', 'published')
    service.updated_by = update_json['updated_by']
    service.updated_reason = update_json['update_reason']
    service.data = service_data

    db.session.add(service)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {0}".format(e))

    if not framework.expired:
        try:
            search_api_client.index(
                service_id,
                service.data,
                supplier.name,
                framework.name)
        except apiclient.HTTPError as e:
            current_app.logger.warning(
                'Failed to add {} to search index: {}'.format(
                    service_id, e.message))

    return jsonify(services=service.serialize()), 201


@main.route('/services/<string:service_id>', methods=['GET'])
def get_service(service_id):
    is_valid_service_id_or_400(service_id)

    service = Service.query.filter(
        Service.service_id == service_id) \
        .filter(Service.framework.has(Framework.expired == false())) \
        .first_or_404()

    return jsonify(services=service.serialize())


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

    service_to_archive = ArchivedService.from_service(service)
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload,
                           ["update_details"])

    update_json = json_payload['update_details']
    validate_updater_json_or_400(update_json)

    if status not in valid_statuses:
        valid_statuses_single_quotes = display_list(
            ["\'{}\'".format(vstatus) for vstatus in valid_statuses]
        )
        abort(400, "\'{0}\' is not a valid status. "
                   "Valid statuses are {1}"
              .format(status, valid_statuses_single_quotes)
              )

    now = datetime.now()
    prior_status = service.status
    service.status = status
    service.updated_at = now
    service.updated_by = update_json['updated_by']
    service.updated_reason = update_json['update_reason']

    db.session.add(service)
    db.session.add(service_to_archive)

    db.session.commit()

    if prior_status != status:

        # If it's being unpublished, delete it from the search api.
        if prior_status == 'published':
            try:
                search_api_client.delete(service_id)
            except apiclient.HTTPError as e:
                current_app.logger.warning(
                    'Failed to delete {} from search index: {}'.format(
                        service_id, e.message))

        # If it's being published, index in the search api.
        if status == 'published':
            try:
                search_api_client.index(
                    service_id,
                    service.data,
                    service.supplier.name,
                    service.framework.name)
            except apiclient.HTTPError as e:
                current_app.logger.warning(
                    'Failed to add {} to search index: {}'.format(
                        service_id, e.message))

    return jsonify(services=service.serialize()), 200
