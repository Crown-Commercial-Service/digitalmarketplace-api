from app import db
from app.api.helpers import Service
from app.models import CaseStudy, Domain

from sqlalchemy import and_, func, or_


class CaseStudyService(Service):
    __model__ = CaseStudy

    def __init__(self, *args, **kwargs):
        super(CaseStudyService, self).__init__(*args, **kwargs)

    def get_approved_case_studies_by_supplier_code(self, supplier_code, domain_id):
        domain_name = (
            db
            .session
            .query(Domain.name)
            .filter(Domain.id == domain_id)
            .subquery()
        )

        cs_id = (
            db.session.query(
                CaseStudy.id.label('case_study_id')
            )
            .filter(
                CaseStudy.supplier_code == supplier_code,
                CaseStudy.status == 'approved',
                CaseStudy.data['service'].astext == domain_name.c.name,
            )
            .subquery()
        )

        case_study = (
            db.session.query(
                domain_name.c.name,
                func.json_object_agg(cs_id.c.case_study_id,
                                     func.json_build_object('client',
                                                            CaseStudy.data['client'].label('client'),
                                                            'opportunity',
                                                            CaseStudy.data['opportunity'].label('opportunity'),
                                                            'outcome',
                                                            CaseStudy.data['outcome'].label('outcome'),
                                                            'project_links',
                                                            CaseStudy.data['project_links'].label('project_links'),
                                                            'referee_contact',
                                                            CaseStudy.data['referee_contact'].label('referee_contact'),
                                                            'referee_email',
                                                            CaseStudy.data['referee_email'].label('referee_email'),
                                                            'referee_positon',
                                                            CaseStudy.data['referee_position']
                                                            .label('referee_position'),
                                                            'referee_name',
                                                            CaseStudy.data['referee_name'].label('referee_name'),
                                                            'roles',
                                                            CaseStudy.data['roles'].label('roles'),
                                                            'service',
                                                            CaseStudy.data['service'].label('service'),
                                                            'timeframe',
                                                            CaseStudy.data['timeframe'].label('timeframe'),
                                                            'title',
                                                            CaseStudy.data['title'].label('title')
                                                            )
                                     ).label('data')
            )
            .filter(CaseStudy.supplier_code == supplier_code,
                    CaseStudy.status == 'approved',
                    CaseStudy.data['service'].astext == domain_name.c.name,
                    )
            .group_by(domain_name.c.name)
            .subquery()
        )

        case_studies_id_array = (
            db.session.query(
                func.array_agg(cs_id.c.case_study_id).label('case_study_id')
            )
            .subquery()
        )

        query = (
            db
            .session
            .query(
                case_studies_id_array.c.case_study_id,
                domain_name.c.name.label('domain_name'),
                case_study.c.data
            )
        )

        return [case_study._asdict() for case_study in query.all()]
