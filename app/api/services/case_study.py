from app import db
from app.api.helpers import Service
from app.models import CaseStudy, Domain

from sqlalchemy import and_, func, or_


class CaseStudyService(Service):
    __model__ = CaseStudy

    def __init__(self, *args, **kwargs):
        super(CaseStudyService, self).__init__(*args, **kwargs)

    def get_approved_case_studies_by_supplier_code(self, supplier_code, domain_id):
        subquery = (
            db
            .session
            .query(
                CaseStudy.id.label('cs_id'),
                CaseStudy.data.label('case_study_data'),
                Domain.name.label('category_name')
            )
            .join(Domain, Domain.name == CaseStudy.data['service'].astext)
            .filter(CaseStudy.supplier_code == supplier_code,
                    CaseStudy.status == 'approved',
                    Domain.id == domain_id)
            .subquery()
        )

        result = (
            db
            .session
            .query(
                subquery.c.category_name,
                func.json_agg(
                    func.json_build_object(
                        'id', subquery.c.cs_id,
                        'data', subquery.c.case_study_data
                    )
                ).label('cs_data')
            )
            .group_by(subquery.c.category_name)
        )
        results = result.one_or_none()
        return results._asdict() if results else {}
