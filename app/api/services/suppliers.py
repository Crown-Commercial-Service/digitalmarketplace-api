from sqlalchemy import func, or_, select, union
from sqlalchemy.orm import joinedload, noload, raiseload
from app import db
from app.api.helpers import Service
from app.models import Supplier, SupplierDomain, User, SupplierFramework, Framework


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
        return (
            db
            .session
            .query(
                Supplier
            )
            .options(
                joinedload(Supplier.domains)
                .joinedload(SupplierDomain.domain)
            )
            .filter(Supplier.code == code)
            .one_or_none()
        )

    def get_suppliers_by_name_keyword(self, keyword):
        return (db.session.query(Supplier)
                .filter(Supplier.name.ilike('%{}%'.format(keyword.encode('utf-8'))))
                .filter(Supplier.status != 'deleted')
                .order_by(Supplier.name.asc())
                .options(
                    joinedload(Supplier.frameworks),
                    joinedload('frameworks.framework'),
                    noload('frameworks.framework.lots'),
                    raiseload('*'))
                .limit(20)
                .all())

    def get_metrics(self):
        supplier_count = (
            db
            .session
            .query(
                func.count(Supplier.id)
            )
            .outerjoin(SupplierFramework)
            .outerjoin(Framework)
            .filter(
                Supplier.abn != Supplier.DUMMY_ABN,
                Supplier.status != 'deleted',
                or_(Framework.slug == 'digital-marketplace', ~Supplier.frameworks.any())
            )
            .scalar()
        )

        return {
            "supplier_count": supplier_count
        }

    def get_supplier_contacts(self, supplier_code):
        authorised_representative = select([Supplier.code, Supplier.data['email'].astext.label('email_address')])
        business_contact = select([Supplier.code, Supplier.data['contact_email'].astext.label('email_address')])
        user_email_addresses = select([User.supplier_code.label('code'), User.email_address])

        email_addresses = (
            union(
                authorised_representative,
                business_contact,
                user_email_addresses
            )
            .alias('email_addresses')
        )

        result = (
            db
            .session
            .query(
                email_addresses.c.email_address
            )
            .filter(
                email_addresses.c.code == supplier_code
            )
            .all()
        )

        return [r._asdict() for r in result]

    def get_suppliers_with_rejected_price(self):
        subquery = (
            db.session.query(SupplierDomain.supplier_id)
            .filter(SupplierDomain.price_status == 'rejected')
            .subquery()
        )
        result = (
            db
            .session
            .query(
                Supplier.code
            )
            .filter(
                Supplier.status != 'deleted',
                Supplier.data['recruiter'].astext.in_(['no', 'both']),
                Supplier.id.in_(subquery)
            )
            .all()
        )

        return [r._asdict() for r in result]
