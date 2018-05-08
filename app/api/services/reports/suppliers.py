from app.api.helpers import Service
from app.models import Supplier
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
