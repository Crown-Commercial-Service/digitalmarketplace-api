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

    def supplier_has_assessment_for_brief(self, supplier_code, brief_id):
        count = (db.session.query(func.count(Assessment.id))
                 .join(SupplierDomain, Domain, BriefAssessment, Brief, Supplier)
                 .filter(Supplier.code == supplier_code, Brief.id == brief_id, Brief.closed_at > pendulum.now('UTC'))
                 .group_by(Brief.id)
                 .scalar())

        return count > 0

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

    def get_open_assessments(self, domain_id=None, supplier_code=None):
        query = (db.session
                   .query(Supplier.code.label('supplier_code'), func.array_agg(Domain.name).label('domains'))
                   .join(SupplierDomain, Assessment)
                   .filter(Assessment.supplier_domain_id == SupplierDomain.id,
                           SupplierDomain.supplier_id == Supplier.id,
                           SupplierDomain.status == 'unassessed',
                           Assessment.active))

        if domain_id:
            query = query.filter(SupplierDomain.domain_id == domain_id)
        else:
            query = query.filter(SupplierDomain.domain_id == Domain.id)

        if supplier_code:
            query = query.filter(Supplier.code == supplier_code)

        results = query.group_by(Supplier.code, Supplier.name).all()

        return [r._asdict() for r in results]
