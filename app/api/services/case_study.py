from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload, raiseload

from app import db
from app.api.helpers import Service
from app.models import CaseStudy, Domain


class CaseStudyService(Service):
    __model__ = CaseStudy

    def __init__(self, *args, **kwargs):
        super(CaseStudyService, self).__init__(*args, **kwargs)

    def get_case_studies_by_supplier_code(self, supplier_code, domain_id):
        subquery = (
            db
            .session
            .query(Domain.name)
            .filter(Domain.id == domain_id)
            .subquery()
        )

        query = (
            db
            .session
            .query(CaseStudy.id, CaseStudy.data)
            .filter(
                CaseStudy.supplier_code == supplier_code,
                CaseStudy.status == 'approved',
                CaseStudy.data['service'].astext == subquery.c.name,
            )
        )

        return [case_study._asdict() for case_study in query.all()]
