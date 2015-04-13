from flask import jsonify, abort, request, current_app

from .. import main
from ...models import Supplier
from ...utils import pagination_links


@main.route('/suppliers', methods=['GET'])
def list_suppliers():

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        abort(400, "Invalid page argument")

    prefix = request.args.get('prefix', '')

    suppliers = Supplier.query

    if prefix:
        # case insensitive LIKE comparison for matching supplier names
        suppliers = suppliers.filter(
            Supplier.name.ilike(prefix + '%'))

    suppliers = suppliers.paginate(
        page=page,
        per_page=current_app.config['DM_API_SUPPLIERS_PAGE_SIZE'],
        error_out=False,
    )

    if not suppliers.items:
        if page > 1:
            abort(404, "Page number out of range")
        else:
            abort(404, "No suppliers found for '{0}'".format(prefix))

    return jsonify(
        suppliers=[supplier.serialize() for supplier in suppliers.items],
        links=pagination_links(
            suppliers,
            '.list_suppliers',
            request.args
        ))


@main.route('/suppliers/<int:supplier_id>', methods=['GET'])
def get_supplier(supplier_id):
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    return jsonify(suppliers=supplier.serialize())
