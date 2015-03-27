from flask import jsonify

from .. import main
from ...models import Supplier


@main.route('/suppliers/<int:supplier_id>', methods=['GET'])
def get_supplier(supplier_id):
    supplier = Supplier.query.filter(
        Supplier.supplier_id == supplier_id
    ).first_or_404()

    return jsonify(suppliers=row2dict(supplier))

"""
Creates a dictionary from sqlAlchemy query object's {column_name}:{value}
@see http://stackoverflow.com/questions/1958219/convert-sqlalchemy-row-object-to-python-dict#comment12704946_1960546
"""
row2dict = lambda row: dict((col, getattr(row, col)) for col in row.__table__.columns.keys())


def jsonify_supplier(supplier):
    data = {
        'id': supplier.id,
        'supplier_id': supplier.supplier_id,
        'name': supplier.name
    }

    return data
