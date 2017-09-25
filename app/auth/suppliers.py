from app import db
from app.models import AuditEvent, AuditTypes, Supplier


def get_supplier(code):
    return Supplier.query.filter(
        Supplier.code == code,
        Supplier.status != 'deleted'
    ).first()


def valid_supplier(user):
    return False if user.role is not 'supplier' or user.supplier_code is None else True


def update_supplier_details(supplier_code, **kwargs):
    """
        Update a supplier. Looks user up in DB, and updates where necessary.
    """

    if supplier_code is None:
        raise ValueError("supplier_code was not provided in kwargs to update supplier function")

    supplier = Supplier.query.filter(Supplier.code == supplier_code).first()

    if supplier is None:
        raise ValueError("Unable to modify supplier. supplier with code {} does not exist".format(supplier_code))

    kwargs.pop('domains', None)
    supplier.update_from_json(kwargs)

    audit = AuditEvent(
        audit_type=AuditTypes.supplier_update,
        user=None,
        data={
            'supplier': supplier.code,
            'update': kwargs
        },
        db_object=supplier
    )

    db.session.add(supplier)
    db.session.add(audit)

    db.session.commit()

    return supplier
