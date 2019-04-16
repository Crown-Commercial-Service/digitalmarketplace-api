from app.api.helpers import Service
from app.models import Supplier, SupplierDomain, Domain
from sqlalchemy import func
from sqlalchemy.sql import text
from app import db


class SuppliersService(Service):
    __model__ = Supplier

    def __init__(self, *args, **kwargs):
        super(SuppliersService, self).__init__(*args, **kwargs)

    def get_unassessed(self):
        s = text(
            "select distinct "
            'd.id "domain_id",'
            'd.name "domain_name",'
            's.id "supplier_id",'
            's.code "supplier_code",'
            's.name "supplier_name",'
            's.data#>>(\'{pricing,"\'||d.name||\'",maxPrice}\')::text[] "supplier_price",'
            'u.supplier_last_logged_in,'
            'cs.id "case_study_id" '
            'from case_study cs '
            'inner join supplier s on s.code = cs.supplier_code '
            "inner join domain d on d.name = cs.data->>'service' "
            'inner join supplier_domain sd on sd.domain_id = d.id '
            '                                 and sd.supplier_id = s.id '
            "                                 and sd.status = 'unassessed'"
            'inner join ('
            '   select supplier_code, '
            '   max(logged_in_at) "supplier_last_logged_in" '
            '   from "user" '
            '   group by supplier_code'
            ') u on u.supplier_code = s.code '
            'where s.data#>>(\'{pricing,"\'||d.name||\'",maxPrice}\')::text[] is not null'
        )
        result = db.session.execute(s)
        return [dict(r) for r in result]

    def get_suppliers(self):
        subquery = (
            db
            .session
            .query(
                SupplierDomain.supplier_id,
                func.json_agg(
                    func.json_build_object(
                        'category', Domain.name,
                        'status', SupplierDomain.status,
                        'price_status', SupplierDomain.price_status
                    )
                ).label('categories')
            )
            .join(Domain)
            .group_by(SupplierDomain.supplier_id)
            .subquery()
        )
        result = (
            db
            .session
            .query(
                Supplier.code,
                Supplier.name,
                Supplier.abn,
                Supplier.status,
                Supplier.creation_time,
                Supplier.data['seller_type']['sme'].astext.label('sme'),
                subquery.columns.categories
            )
            .join(subquery, Supplier.id == subquery.columns.supplier_id)
            .order_by(Supplier.code)
            .all()
        )

        return [r._asdict() for r in result]
