from flask import jsonify, abort, request, current_app
from sqlalchemy.exc import IntegrityError, DataError

from app.main import main
from app.models import db, Brief, WorkOrder
from app.utils import (
    get_json_from_request, json_has_required_keys, get_int_or_400,
    pagination_links, get_valid_page_or_1, url_for,
    get_positive_int_or_400
)

from app.service_utils import validate_and_return_supplier


def get_brief_for_new_work_order(work_order_json):
    json_has_required_keys(work_order_json, ['briefId'])
    brief_id = work_order_json['briefId']

    try:
        brief = Brief.query.get(brief_id)
    except DataError:
        brief = None

    if brief is None:
        abort(400, "Invalid opportunity ID '{}'".format(brief_id))

    if brief.status != 'closed':
        abort(400, "Opportunity must be closed")

    return brief


def get_work_order_json():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['workOrder'])
    return json_payload['workOrder']


def save_work_order(work_order):
    db.session.add(work_order)

    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig)

    db.session.commit()


@main.route('/work-orders', methods=['POST'])
def create_work_order():
    work_order_json = get_work_order_json()
    supplier = validate_and_return_supplier(work_order_json)
    brief = get_brief_for_new_work_order(work_order_json)

    if WorkOrder.query.filter_by(brief_id=brief.id).first() is not None:
        abort(400, "Work order already exists for opportunity '{}'".format(brief.id))

    work_order = WorkOrder(
        data=work_order_json,
        supplier=supplier,
        brief=brief,
    )
    save_work_order(work_order)

    return jsonify(workOrder=work_order.serialize()), 201


@main.route('/work-orders/<int:work_order_id>', methods=['PATCH'])
def update_work_order(work_order_id):
    work_order_json = get_work_order_json()

    work_order = WorkOrder.query.get(work_order_id)
    if work_order is None:
        abort(404, "Work order '{}' does not exist".format(work_order_id))

    work_order.update_from_json(work_order_json)
    save_work_order(work_order)

    return jsonify(workOrder=work_order.serialize()), 200


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
