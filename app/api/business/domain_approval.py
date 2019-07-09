from app.api.services import (
    AuditTypes, evidence_service, evidence_assessment_service, users, suppliers, domain_service, supplier_domain_service
)
from app.api.business.errors import DomainApprovalException
from app.models import db
from app.tasks import publish_tasks


class DomainApproval(object):
    def __init__(self, evidence_id=None, actioned_by=None):
        if not actioned_by or not str(actioned_by).isdigit():
            raise DomainApprovalException('An admin user id must be supplied')
        self.user = users.find(id=int(actioned_by)).one_or_none()
        if not self.user or self.user.role != 'admin':
            raise DomainApprovalException('Invalid user id in actioned_by')
        self.evidence = evidence_service.find(id=evidence_id).one_or_none()
        if not self.evidence or not self.evidence.status == 'submitted':
            raise DomainApprovalException('Evidence id is invalid or is not submitted')
        self.actioned_by = actioned_by

    def __commit(self):
        try:
            db.session.commit()
        except DBAPIError as e:
            db.session.rollback()
            raise DomainApprovalException("Database Error: {0}".format(e))

    def approve_domain(self):

        supplier = suppliers.get_supplier_by_code(self.evidence.supplier_code)
        if not supplier:
            raise DomainApprovalException('Invalid suppier code in evidence')

        domain = domain_service.find(id=self.evidence.domain_id).one_or_none()
        if not domain:
            raise DomainApprovalException('Invalid domain id in evidence')

        # insert the supplier_domain as assessed for this supplier and domain
        supplier_domain_service.set_supplier_domain_status(
            supplier.id,
            domain.id,
            'assessed',
            'approved',
            do_commit=False
        )

        # set the evidence as approved
        self.evidence.approve()
        evidence_service.save_evidence(self.evidence, do_commit=False)

        # update the supplier's pricing for the evidence's domain
        supplier_data = supplier.data.copy()
        if 'pricing' not in supplier_data:
            supplier_data['pricing'] = {}
        supplier_data['pricing'][domain.name] = {'maxPrice': str(self.evidence.data['maxDailyRate'])}
        supplier.data.update({'pricing': supplier_data['pricing']})
        suppliers.save_supplier(supplier, do_commit=False)

        # create the evidence assessment outcome
        evidence_assessment = evidence_assessment_service.create_assessment(
            evidence_id=self.evidence.id,
            user_id=self.actioned_by,
            status='approved',
            do_commit=False
        )

        self.__commit()

        try:
            publish_tasks.evidence.delay(
                publish_tasks.compress_evidence(self.evidence),
                'approved',
                actioned_by=self.actioned_by,
                evidence_assessment=evidence_assessment.serialize(),
                domain=domain.name,
                supplier_code=supplier.code
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
