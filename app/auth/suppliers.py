from app.models import Supplier


def get_supplier(code):
    return Supplier.query.filter(
        Supplier.code == code,
        Supplier.status != 'deleted'
    ).first()
