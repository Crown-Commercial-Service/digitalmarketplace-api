from app import db
from app.api.helpers import Service
from app.models import CaseStudy, Domain

from sqlalchemy import and_, func, or_


class CaseStudyService(Service):
    __model__ = CaseStudy

    def __init__(self, *args, **kwargs):
        super(CaseStudyService, self).__init__(*args, **kwargs)

    def get_approved_case_studies_by_supplier_code(self, supplier_code, domain_id):
        # domain_name = (
        #     db
        #     .session
        #     .query(Domain.name)
        #     .filter(Domain.id == domain_id)
        #     .subquery()
        # )

        # case_study = (
        #     db.session.query(CaseStudy.id.label('cs_id'), CaseStudy.data)
        #     .filter(CaseStudy.supplier_code == supplier_code,
        #             CaseStudy.status == 'approved',
        #             CaseStudy.data['service'].astext == domain_name.c.name
        #             )
        # )

        # cs_data = [value._asdict() for value in case_study.all()]
        # case_studies = {}
        # case_studies['cs_data'] = cs_data

        # # incase there is no category name provide an empty string
        # category_name = ""
        # for k, v in case_study.all():
        #     for k1, v1 in v.items():
        #         if k1 == 'service':
        #             category_name = v1

        # case_studies['category_name'] = category_name

        # return case_studies


        # domain_name = (
        #     db
        #     .session
        #     .query(Domain.name.label('category_name'))
        #     .filter(Domain.id == domain_id)
        #     .subquery()
        # )

        # case_study = (
        #     db.session.query(CaseStudy.id.label('cs_id'), CaseStudy.data.label('case_study_data'))
        #     .filter(CaseStudy.supplier_code == supplier_code,
        #             CaseStudy.status == 'approved',
        #             CaseStudy.data['service'].astext == domain_name.c.category_name
        #             )
        #     .subquery()
        # )

        # result = (
        #     db
        #     .session
        #     .query(domain_name.c.category_name,  
        #     func.json_agg(
        #             func.json_build_object(
        #                 'id', case_study.c.cs_id,
        #                 'data', case_study.c.case_study_data
        #             )
        #         ).label('cs_data')
        #     )
        #     .group_by(domain_name.c.category_name)
        # )

        # return [a._asdict() for a in result.all()]

        test = (
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
            .query(test.c.category_name,  
            func.json_agg(
                    func.json_build_object(
                        'id', test.c.cs_id,
                        'data', test.c.case_study_data
                    )
                ).label('cs_data')
            )
            .group_by(test.c.category_name)
        )
        values ={}
        for a in result.all():
            values = a._asdict()
        
        return values
        




# select q1.category, json_agg(
# 	json_build_object(
# 		'id', q1.id,
# 		'data', q1.data
# 	)
# ) case_studies
# from (
# 	select cs.id, cs.data, d.name category
# 	from case_study cs
# 	inner join domain d on d.name = cs.data ->> 'service'
# 	where 
# 		cs.supplier_code = 869 and
# 		cs.status = 'approved' and
# 		d.id = 6
# ) q1
# group by q1.category