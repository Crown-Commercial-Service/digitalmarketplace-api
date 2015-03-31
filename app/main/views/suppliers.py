from flask import jsonify, abort, request

from .. import main
from ...models import Supplier


@main.route('/suppliers', methods=['GET'])
def get_suppliers_by_prefix():

    prefix = request.args.get('prefix', '')

    if not prefix:
        abort(400, "No supplier name prefix provided")

    # case insensitive LIKE comparison for matching supplier names
    suppliers = Supplier.query.filter(
        Supplier.name.ilike(prefix + '%')
    ).all()

    if not suppliers:
        abort(404, "No suppliers found for \'%s\'" % prefix)

    suppliers_json = [supplier.serialize() for supplier in suppliers]

    return jsonify(suppliers=suppliers_json)


@main.route('/suppliers/<int:supplier_id>', methods=['GET'])
def get_supplier(supplier_id):
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    return jsonify(suppliers=supplier.serialize())
