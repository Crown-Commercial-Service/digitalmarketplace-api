from flask import jsonify, abort, request, current_app
from sqlalchemy.exc import IntegrityError, DataError

from .. import main
from ...models import db, Brief, WorkOrder, AuditEvent
from ...utils import (
    get_json_from_request, json_has_required_keys, get_int_or_400,
    pagination_links, get_valid_page_or_1, url_for,
    validate_and_return_updater_request, get_positive_int_or_400
)

from ...service_utils import validate_and_return_supplier
from enum import Enum, unique


@unique
class WorkOrderAuditTypes(Enum):
    create_work_order = 'create_work_order'


@main.route('/work-orders', methods=['POST'])
def create_work_order():
    json_payload = get_json_from_request()
    updater_json = validate_and_return_updater_request()

    json_has_required_keys(json_payload, ['workOrder'])
    work_order_json = json_payload['workOrder']
    json_has_required_keys(work_order_json, ['briefId', 'supplierCode'])

    try:
        brief = Brief.query.get(work_order_json['briefId'])
    except DataError:
        brief = None

    if brief is None:
        abort(400, "Invalid brief ID '{}'".format(work_order_json['briefId']))

    if brief.status != 'closed':
        abort(400, "Brief must be closed")

    supplier = validate_and_return_supplier(work_order_json)

    if WorkOrder.query.filter(WorkOrder.brief == brief).first():
        abort(400, "Work order already exists for brief '{}'".format(brief.id))

    work_order = WorkOrder(
        data=work_order_json,
        supplier=supplier,
        brief=brief,
    )

    db.session.add(work_order)

    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig)

    audit = AuditEvent(
        audit_type=WorkOrderAuditTypes.create_work_order,
        user=updater_json['updated_by'],
        data={
            'workOrderId': work_order.id,
            'workOrderJson': work_order_json,
        },
        db_object=work_order,
    )

    db.session.add(audit)
    db.session.commit()

    return jsonify(workOrder=work_order.serialize()), 201


@main.route('/work-orders/<int:work_order_id>', methods=['GET'])
def get_work_order(work_order_id):
    work_order = WorkOrder.query.filter(
        WorkOrder.id == work_order_id
    ).first_or_404()

    return jsonify(workOrder=work_order.serialize())


@main.route('/work-orders', methods=['GET'])
def list_work_orders():
    page = get_valid_page_or_1()
    brief_id = get_int_or_400(request.args, 'brief_id')
    supplier_code = get_int_or_400(request.args, 'supplier_code')

    work_orders = WorkOrder.query
    if supplier_code is not None:
        work_orders = work_orders.filter(WorkOrder.supplier_code == supplier_code)

    if brief_id is not None:
        work_orders = work_orders.filter(WorkOrder.brief_id == brief_id)

    if brief_id or supplier_code:
        return jsonify(
            workOrders=[work_order.serialize() for work_order in work_orders.all()],
            links={'self': url_for('.list_work_orders', supplier_code=supplier_code, brief_id=brief_id)}
        )

    results_per_page = get_positive_int_or_400(
        request.args,
        'per_page',
        current_app.config['DM_API_PAGE_SIZE']
    )

    work_orders = work_orders.paginate(
        page=page,
        per_page=results_per_page
    )

    return jsonify(
        workOrders=[work_order.serialize() for work_order in work_orders.items],
        links=pagination_links(
            work_orders,
            '.list_work_orders',
            request.args
        )
    )
