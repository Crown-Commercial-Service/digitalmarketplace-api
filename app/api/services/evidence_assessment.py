from app.models import EvidenceAssessment
from app.api.helpers import Service
from app import db


class EvidenceAssessmentService(Service):
    __model__ = EvidenceAssessment

    def __init__(self, *args, **kwargs):
        super(EvidenceAssessmentService, self).__init__(*args, **kwargs)

    def get_assessment_for_rejected_evidence(self, evidence_id):
        if not evidence_id:
            return False
        feedback = (
            db.session.query(EvidenceAssessment)
            .filter(
                EvidenceAssessment.evidence_id == evidence_id,
                EvidenceAssessment.status == 'rejected'
            )
            .order_by(EvidenceAssessment.created_at.desc()).first()
        )
        return feedback

    def create_assessment(self, evidence_id=None, user_id=None, status=None, data=None, do_commit=True):
        if not data:
            data = {}
        if not evidence_id or not user_id or not status:
            return False
        evidence_assessment = EvidenceAssessment(
            evidence_id=evidence_id,
            user_id=user_id,
            status=status,
            data=data
        )
        self.save(evidence_assessment, do_commit)
        return evidence_assessment
