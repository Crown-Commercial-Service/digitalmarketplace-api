from sqlalchemy import func
from sqlalchemy.orm import joinedload, Load
from app import db
from app.api.helpers import Service
from app.models import Supplier, SupplierDomain, Domain


class SuppliersService(Service):
    __model__ = Supplier

    def __init__(self, *args, **kwargs):
        super(SuppliersService, self).__init__(*args, **kwargs)

    def get_suppliers_by_contact_email(self, emails):
        return (db.session.query(Supplier)
                .filter(func.lower(Supplier.data['contact_email'].astext).in_(emails))
                .filter(Supplier.status != 'deleted')
                .all())

    def get_supplier_by_code(self, code):
        return (db.session.query(Supplier).options(
            joinedload(Supplier.domains, innerjoin=True)
            .joinedload(SupplierDomain.domain, innerjoin=True),
            Load(Supplier)
        )
            .filter(Supplier.code == code)
            .one_or_none())
