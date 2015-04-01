from flask import jsonify, abort, request

from .. import main
from ...models import Supplier

API_FETCH_PAGE_SIZE = 2


@main.route('/suppliers', methods=['GET'])
def get_suppliers_by_prefix():

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")

    prefix = request.args.get('prefix', '')

    if not prefix:
        abort(400, "No supplier name prefix provided")

    # case insensitive LIKE comparison for matching supplier names
    suppliers = Supplier.query.filter(
        Supplier.name.ilike(prefix + '%')
    )

    if not suppliers.all():
        abort(404, "No suppliers found for \'{0}\'".format(prefix))

    # suppliers_json = [supplier.serialize() for supplier in suppliers]

    suppliers = suppliers.paginate(
        page=page,
        per_page=API_FETCH_PAGE_SIZE,
        error_out=False
    )

    if page > 1 and not suppliers:
        abort(404, "Page number out of range")
    return jsonify(
        suppliers=[supplier.serialize() for supplier in suppliers.items],
        links=Supplier.pagination_links(
            suppliers,
            '.get_suppliers_by_prefix',
            request.args
        ))


@main.route('/suppliers/<int:supplier_id>', methods=['GET'])
def get_supplier(supplier_id):
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    return jsonify(suppliers=supplier.serialize())
