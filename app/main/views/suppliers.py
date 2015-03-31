from flask import jsonify
from flask import request

from .. import main
from ...models import Supplier


@main.route('/suppliers', methods=['GET'])
def get_suppliers_by_prefix():

    prefix = request.args.get('prefix', '')

    if not prefix:
        return '<h1>Oops, please include a query with a `prefix` key</h1>'

    suppliers = Supplier.query.filter(
        Supplier.name.ilike(prefix + '%')
    ).all()

    if not suppliers:
        return '<h1>Oops, no suppliers found with names that start with "' \
               + prefix + '"</h1>'

    suppliers_json = []

    for supplier in suppliers:
        suppliers_json.append(jsonify_supplier(supplier))

    return jsonify(suppliers=suppliers_json)


@main.route('/suppliers/<int:supplier_id>', methods=['GET'])
def get_supplier(supplier_id):
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    return jsonify(suppliers=supplier.serialize())
