from sqlalchemy import or_, and_
from app.models import Evidence, Supplier, Brief, Domain
from app.api.helpers import Service
from app import db


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

    def get_latest_evidence_for_supplier_and_domain(self, domain_id, supplier_code):
        evidence = self.filter(
            Evidence.supplier_code == supplier_code,
            Evidence.domain_id == domain_id
        ).order_by(Evidence.id.desc()).first()
        return evidence

    def get_previous_submitted_evidence_for_supplier_and_domain(self, evidence_id, domain_id, supplier_code):
        evidence = self.filter(
            Evidence.supplier_code == supplier_code,
            Evidence.domain_id == domain_id,
            Evidence.submitted_at.isnot(None),
            or_(Evidence.approved_at.isnot(None), Evidence.rejected_at.isnot(None)),
            Evidence.id != evidence_id
        ).order_by(Evidence.id.desc()).first()
        return evidence

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
