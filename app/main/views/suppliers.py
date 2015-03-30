from flask import jsonify

from .. import main
from ...models import Supplier


@main.route('/suppliers/<int:supplier_id>', methods=['GET'])
def get_supplier(supplier_id):
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    return jsonify(suppliers=jsonify_supplier(supplier))


def jsonify_supplier(supplier):
    data = {
        'id': supplier.id,
        'supplier_id': supplier.supplier_id,
        'name': supplier.name
    }

    return data
