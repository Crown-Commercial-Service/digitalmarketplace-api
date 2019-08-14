from app.api.services import evidence_service, evidence_assessment_service, audit_service, audit_types
from app.api.business.domain_criteria import DomainCriteria
from app.api.business.errors import DomainCriteriaInvalidRateException


def get_all_evidence(supplier_code):
    evidence_collection = evidence_service.get_all_evidence(supplier_code=supplier_code)
    data = []
    for evidence_data in evidence_collection:
        try:
            evidence_data['criteriaNeeded'] = int(
                DomainCriteria(
                    domain_id=evidence_data.get('domain_id', None),
                    rate=evidence_data.get('maxDailyRate', None)
                ).get_criteria_needed()
            )
        except DomainCriteriaInvalidRateException as e:
            pass
        evidence_data['assessment'] = None
        if evidence_data['status'] in ['rejected', 'assessed']:
            assessment = evidence_assessment_service.get_assessment_for_evidence(evidence_data['id'])
            if assessment:
                evidence_data['assessment'] = assessment.serialize()
                evidence_data['feedback_created_at'] = assessment.created_at
        data.append(evidence_data)
    return data


def delete_draft_evidence(evidence_id, actioned_by):
    evidence = evidence_service.get_evidence_by_id(evidence_id)
    if not evidence or not evidence.status == 'draft':
        return False
    evidence_service.delete(evidence)
    audit_service.log_audit_event(
        audit_type=audit_types.evidence_draft_deleted,
        user=actioned_by,
        data={
            "id": evidence.id,
            "domainId": evidence.domain_id,
            "briefId": evidence.brief_id,
            "status": evidence.status,
            "supplierCode": evidence.supplier_code,
            "data": evidence.data
        },
        db_object=evidence
    )
    return True
