from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload, raiseload
from sqlalchemy.types import Integer

from app import db
from app.api.helpers import Service
from app.models import Brief, Domain, DomainCriteria, Evidence, EvidenceAssessment, Supplier


class EvidenceService(Service):
    __model__ = Evidence

    def __init__(self, *args, **kwargs):
        super(EvidenceService, self).__init__(*args, **kwargs)

    def get_domain_ids_with_evidence(self, supplier_code):
        query = (
            db.session.query(Evidence.domain_id)
            .filter(Evidence.supplier_code == supplier_code)
        )
        return [domain_id[0] for domain_id in query.distinct()]

    def get_evidence_by_id(self, evidence_id):
        query = (
            db.session.query(Evidence)
            .filter(
                Evidence.id == evidence_id
            )
            .options(
                joinedload(Evidence.supplier).joinedload(Supplier.signed_agreements),
                joinedload(Evidence.supplier).joinedload(Supplier.domains),
                joinedload(Evidence.user),
                joinedload(Evidence.brief).joinedload(Brief.clarification_questions),
                joinedload(Evidence.brief).joinedload(Brief.work_order),
                joinedload(Evidence.domain),
                raiseload('*')
            )
        )
        evidence = query.one_or_none()
        return evidence

    def get_latest_evidence_for_supplier_and_domain(self, domain_id, supplier_code):
        query = (
            db.session.query(Evidence)
            .filter(
                Evidence.supplier_code == supplier_code,
                Evidence.domain_id == domain_id
            )
            .options(
                joinedload(Evidence.supplier).joinedload(Supplier.signed_agreements),
                joinedload(Evidence.supplier).joinedload(Supplier.domains),
                joinedload(Evidence.user),
                joinedload(Evidence.brief).joinedload(Brief.clarification_questions),
                joinedload(Evidence.brief).joinedload(Brief.work_order),
                joinedload(Evidence.domain),
                raiseload('*')
            )
            .order_by(Evidence.id.desc())
        )
        evidence = query.first()
        return evidence

    def get_previous_submitted_evidence_for_supplier_and_domain(self, evidence_id, domain_id, supplier_code):
        query = (
            db.session.query(Evidence)
            .filter(
                Evidence.supplier_code == supplier_code,
                Evidence.domain_id == domain_id,
                Evidence.submitted_at.isnot(None),
                or_(Evidence.approved_at.isnot(None), Evidence.rejected_at.isnot(None)),
                Evidence.id != evidence_id
            )
            .options(
                joinedload(Evidence.supplier).joinedload(Supplier.signed_agreements),
                joinedload(Evidence.supplier).joinedload(Supplier.domains),
                joinedload(Evidence.user),
                joinedload(Evidence.brief).joinedload(Brief.clarification_questions),
                joinedload(Evidence.brief).joinedload(Brief.work_order),
                joinedload(Evidence.domain),
                raiseload('*')
            )
            .order_by(Evidence.id.desc())
        )
        evidence = query.first()
        return evidence

    def get_approved_evidence(self, evidence_id):
        category_name_max_daily_rate = (
            db.session.query(
                Domain.name.label('category'),
                Evidence.data['maxDailyRate'].label('maxDailyRate')
            )
            .join(Evidence, Evidence.domain_id == Domain.id)
            .filter(Evidence.id == evidence_id)
            .subquery()
        )

        evidence_domain_criteria = (
            db.session.query(
                Evidence.id.label('evidence_id'),
                func.json_array_elements_text(Evidence.data['criteria']).label('domain_criteria_id')
            )
            .filter(Evidence.id == evidence_id)
            .subquery()
        )

        subquery = (
            db.session.query(
                evidence_domain_criteria.c.domain_criteria_id,
                DomainCriteria.name.label('dc_name'),
                Evidence.data['evidence'][evidence_domain_criteria.c.domain_criteria_id].label('evidence_data')
            )
            .join(DomainCriteria, DomainCriteria.id == evidence_domain_criteria.c.domain_criteria_id.cast(Integer))
            .filter(Evidence.id == evidence_id)
            .subquery()
        )

        evidence_data = (
            db.session.query(
                category_name_max_daily_rate.c.category,
                func.json_agg(
                    func.json_build_object(
                        'dc_id', subquery.c.domain_criteria_id,
                        'domain_criteria_name', subquery.c.dc_name,
                        'evidence_data', subquery.c.evidence_data
                    )
                ).label('evidence')
            )
            .group_by(category_name_max_daily_rate.c.category)
            .subquery()
        )

        result = (
            db.session.query(
                category_name_max_daily_rate.c.category,
                category_name_max_daily_rate.c.maxDailyRate,
                evidence_data.c.evidence
            )
        )

        results = result.one_or_none()
        return results._asdict() if results else {}

    def get_all_evidence(self, supplier_code=None):
        query = (
            db.session.query(
                Evidence.id.label('id'),
                Evidence.status,
                Evidence.created_at,
                Evidence.submitted_at,
                Evidence.approved_at,
                Evidence.rejected_at,
                Evidence.data.label('data'),
                Evidence.data['maxDailyRate'].astext.label('maxDailyRate'),
                Supplier.name.label('supplier_name'), Supplier.code.label('supplier_code'),
                Brief.id.label('brief_id'), Brief.closed_at.label('brief_closed_at'),
                Brief.data['title'].astext.label('brief_title'),
                Domain.name.label('domain_name'), Domain.id.label('domain_id'),
                Domain.price_maximum.label('domain_price_maximum')
            )
            .join(Domain, Evidence.domain_id == Domain.id)
            .join(Supplier, Evidence.supplier_code == Supplier.code)
            .outerjoin(Brief, Evidence.brief_id == Brief.id)
            .order_by(Evidence.submitted_at.desc(), Evidence.created_at.desc())
        )
        if supplier_code:
            query = query.filter(Evidence.supplier_code == supplier_code)
        return [e._asdict() for e in query.all()]

    def get_all_submitted_evidence(self):
        query = (
            db.session.query(
                Evidence.id.label('id'), Evidence.submitted_at,
                Evidence.data.label('data'),
                Evidence.data['maxDailyRate'].astext.label('maxDailyRate'),
                Supplier.name.label('supplier_name'), Supplier.code.label('supplier_code'),
                Brief.id.label('brief_id'), Brief.closed_at.label('brief_closed_at'),
                Brief.data['title'].astext.label('brief_title'),
                Domain.name.label('domain_name'), Domain.id.label('domain_id'),
                Domain.price_maximum.label('domain_price_maximum')
            )
            .filter(
                Evidence.submitted_at.isnot(None),
                Evidence.approved_at.is_(None),
                Evidence.rejected_at.is_(None)
            )
            .join(Domain, and_(Evidence.domain_id == Domain.id))
            .join(Supplier, and_(Evidence.supplier_code == Supplier.code))
            .outerjoin(Brief, and_(Evidence.brief_id == Brief.id))
            .order_by(Evidence.submitted_at.asc())
        )
        return query.all()

    def get_approved_domain_criteria(self, evidence_id, previous_evidence_id):
        previous_rejected_criteria = (
            db.session
              .query(func.json_object_keys(EvidenceAssessment.data['failed_criteria']))
              .filter(EvidenceAssessment.evidence_id == previous_evidence_id)
              .subquery()
        )

        previous_submitted_criteria = (
            db.session
              .query(func.json_array_elements_text(Evidence.data['criteria']).label('id'))
              .filter(Evidence.id == previous_evidence_id)
              .subquery()
        )

        submitted_criteria = (
            db.session
              .query(func.json_array_elements_text(Evidence.data['criteria']).label('id'))
              .filter(Evidence.id == evidence_id)
              .subquery()
        )

        approved_criteria = (
            db.session
              .query(submitted_criteria.columns.id)
              .filter(
                  submitted_criteria.columns.id.notin_(previous_rejected_criteria),
                  submitted_criteria.columns.id.in_(previous_submitted_criteria))
              .all()
        )

        return [criteria.id for criteria in approved_criteria]

    def get_submitted_evidence(self, evidence_id):
        query = (
            db.session.query(
                Evidence.id.label('id'), Evidence.submitted_at,
                Evidence.data.label('data'),
                Evidence.data['maxDailyRate'].astext.label('maxDailyRate'),
                Supplier.name.label('supplier_name'), Supplier.code.label('supplier_code'),
                Brief.id.label('brief_id'), Brief.closed_at.label('brief_closed_at'),
                Brief.data['title'].astext.label('brief_title'),
                Domain.name.label('domain_name'), Domain.id.label('domain_id'),
                Domain.price_maximum.label('domain_price_maximum')
            )
            .filter(
                Evidence.submitted_at.isnot(None),
                Evidence.approved_at.is_(None),
                Evidence.rejected_at.is_(None),
                Evidence.id == evidence_id
            )
            .join(Domain, and_(Evidence.domain_id == Domain.id))
            .join(Supplier, and_(Evidence.supplier_code == Supplier.code))
            .outerjoin(Brief, and_(Evidence.brief_id == Brief.id))
            .order_by(Evidence.submitted_at.asc())
        )
        return query.one_or_none()

    def supplier_has_assessment_for_brief(self, supplier_code, brief_id):
        evidence = self.filter(
            Evidence.supplier_code == supplier_code,
            Evidence.brief_id == brief_id
        ).order_by(Evidence.id.desc()).first()
        return True if evidence else False

    def create_evidence(self, domain_id, supplier_code, user_id, brief_id=None, data=None, do_commit=True):
        if not data:
            data = {}
        evidence = Evidence(
            domain_id=domain_id,
            supplier_code=supplier_code,
            brief_id=brief_id,
            user_id=user_id,
            data=data
        )
        return self.save(evidence, do_commit)

    def save_evidence(self, evidence, do_commit=True):
        return self.save(evidence, do_commit)
