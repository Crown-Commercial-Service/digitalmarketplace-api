from app.api.services import (
    AuditTypes, evidence_service, evidence_assessment_service, users, suppliers, domain_service, supplier_domain_service
)
from app.api.business.errors import DomainApprovalException
from app.models import db
from app.tasks import publish_tasks


class DomainApproval(object):
    def __init__(self, evidence_id=None, actioned_by=None):
        if not actioned_by or not str(actioned_by).isdigit():
            raise DomainApprovalException('An admin or assessor user id must be supplied')
        self.user = users.get_by_id(int(actioned_by))
        if not self.user or self.user.role not in ['admin', 'assessor']:
            raise DomainApprovalException('Invalid user id in actioned_by')
        self.evidence = evidence_service.get_evidence_by_id(evidence_id)
        if not self.evidence or not self.evidence.status == 'submitted':
            raise DomainApprovalException('Evidence id is invalid or is not submitted')
        self.actioned_by = actioned_by

    def __commit(self):
        try:
            db.session.commit()
        except DBAPIError as e:
            db.session.rollback()
            raise DomainApprovalException("Database Error: {0}".format(e))

    def approve_domain(self, failed_criteria, vfm):
        data = {
            "failed_criteria": {}
        }
        if failed_criteria:
            data['failed_criteria'] = failed_criteria
        if vfm is not None:
            data['vfm'] = vfm
        # set the evidence as approved
        self.evidence.approve()
        evidence_service.save_evidence(self.evidence, do_commit=False)

        # create the evidence assessment outcome
        evidence_assessment = evidence_assessment_service.create_assessment(
            evidence_id=self.evidence.id,
            user_id=self.actioned_by,
            status='approved',
            data=data,
            do_commit=False
        )

        self.__commit()

        try:
            publish_tasks.evidence.delay(
                publish_tasks.compress_evidence(self.evidence),
                'approved',
                actioned_by=self.actioned_by,
                evidence_assessment=evidence_assessment.serialize(),
                domain=self.evidence.domain.name,
                supplier_code=self.evidence.supplier.code
            )
        except Exception as e:
            pass

        return evidence_assessment

    def reject_domain(self, failed_criteria, vfm):

        data = {
            "failed_criteria": {}
        }
        if failed_criteria:
            data['failed_criteria'] = failed_criteria
        if vfm is not None:
            data['vfm'] = vfm
        # set the evidence as rejected
        self.evidence.reject()
        evidence_service.save_evidence(self.evidence, do_commit=False)

        # create the evidence assessment outcome
        evidence_assessment = evidence_assessment_service.create_assessment(
            evidence_id=self.evidence.id,
            user_id=self.actioned_by,
            status='rejected',
            data=data,
            do_commit=False
        )

        self.__commit()

        try:
            publish_tasks.evidence.delay(
                publish_tasks.compress_evidence(self.evidence),
                'rejected',
                actioned_by=self.actioned_by,
                evidence_assessment=evidence_assessment.serialize(),
                domain=self.evidence.domain.name,
                supplier_code=self.evidence.supplier.code
            )
        except Exception as e:
            pass

        return evidence_assessment
