import pendulum
from sqlalchemy import func

from app import db
from app.api.helpers import Service
from app.models import (Assessment, Brief, BriefAssessment, Domain, Supplier,
                        SupplierDomain)


class AssessmentsService(Service):
    __model__ = Assessment

    def __init__(self, *args, **kwargs):
        super(AssessmentsService, self).__init__(*args, **kwargs)

    def get_supplier_assessments(self, code):
        id = db.session.query(Supplier.id).filter(Supplier.code == code)

        assessments = db.session.query(Assessment.created_at, Domain.name.label('domain_name'),
                                       SupplierDomain.status.label('domain_status'),
                                       Brief.id, Brief.data['title'].astext.label('name'),
                                       Brief.closed_at)\
            .join(SupplierDomain, Domain, BriefAssessment, Brief)\
            .filter(SupplierDomain.supplier_id == id, Assessment.active, Brief.closed_at > pendulum.now('UTC'))\
            .order_by(Assessment.created_at.desc())\
            .all()

        return [a._asdict() for a in assessments]

    def get_open_assessments(self):
        results = (db.session
                   .query(Supplier.code.label('supplier_code'), func.array_agg(Domain.name).label('domains'))
                   .join(SupplierDomain, Assessment)
                   .filter(Assessment.supplier_domain_id == SupplierDomain.id,
                           SupplierDomain.supplier_id == Supplier.id,
                           SupplierDomain.domain_id == Domain.id,
                           SupplierDomain.status == 'unassessed',
                           Assessment.active)
                   .group_by(Supplier.code, Supplier.name)
                   .all())

        return [r._asdict() for r in results]
