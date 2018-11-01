from flask import jsonify

from app.models import Supplier


def get_supplier(code):
    supplier = Supplier.query.filter(
        Supplier.code == code,
        Supplier.status != 'deleted'
    ).first_or_404()

    return jsonify(supplier.serializable), 200
