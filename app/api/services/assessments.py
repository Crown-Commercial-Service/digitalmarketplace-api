import pendulum
from app.api.helpers import Service
from app import db
from app.models import Assessment, Domain, SupplierDomain, Brief, BriefAssessment, Supplier


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
