from flask import jsonify, abort, current_app, request
from app.main import main
from app.utils import get_json_from_request
from app.api.business.domain_approval import DomainApproval
from app.api.business.domain_criteria import DomainCriteria
from app.api.business.evidence_business import get_all_evidence, delete_draft_evidence
from app.api.business.errors import DomainCriteriaInvalidRateException, DomainApprovalException
from app.api.services import (
    evidence_service, evidence_assessment_service, domain_criteria_service, users, suppliers, audit_service,
    audit_types
)
from app.emails.evidence_assessments import (
    send_evidence_assessment_approval_notification,
    send_evidence_assessment_rejection_notification
)


@main.route('/evidence', methods=['GET'])
def get_all_evidence_submitted():
    evidence_submitted = evidence_service.get_all_submitted_evidence()
    data = []
    for evidence in evidence_submitted:
        evidence_data = evidence._asdict()
        try:
            evidence_data['criteriaNeeded'] = int(
                DomainCriteria(
                    domain_id=evidence_data.get('domain_id', None),
                    rate=evidence_data.get('maxDailyRate', None)
                ).get_criteria_needed()
            )
        except DomainCriteriaInvalidRateException as e:
            abort(400, str(e))
        data.append(evidence_data)
    return jsonify(evidence=data), 200


@main.route('/evidence/all', methods=['GET'])
def view_all_evidence():
    supplier_code = request.args.get('supplier_code', None)
    evidence = get_all_evidence(supplier_code)
    return jsonify(evidence=evidence), 200


@main.route('/evidence/<int:evidence_id>', methods=['GET'])
def get_evidence(evidence_id):
    evidence = evidence_service.get_submitted_evidence(evidence_id)
    evidence_data = {}
    if evidence:
        evidence_data = evidence._asdict()
        if evidence_data:
            domain_criteria = domain_criteria_service.get_criteria_by_domain_id(evidence_data['domain_id'])
            evidence_data['domain_criteria'] = [x.serialize() for x in domain_criteria]
            previous_evidence = evidence_service.get_previous_submitted_evidence_for_supplier_and_domain(
                evidence_id,
                evidence.domain_id,
                evidence.supplier_code
            )

            approved_criteria = []
            evidence_data['previous_id'] = False

            if previous_evidence:
                approved_criteria = evidence_service.get_approved_domain_criteria(evidence_id, previous_evidence.id)
                evidence_data['previous_id'] = previous_evidence.id
                evidence_data['previous_rejected'] = (
                    True if previous_evidence.status == 'rejected' else False
                )

            evidence_data['approvedCriteria'] = approved_criteria

            try:
                evidence_data['criteriaNeeded'] = int(
                    DomainCriteria(
                        domain_id=evidence_data.get('domain_id', None),
                        rate=evidence_data.get('maxDailyRate', None)
                    ).get_criteria_needed()
                )
            except DomainCriteriaInvalidRateException as e:
                abort(400, str(e))
    return jsonify(evidence=evidence_data), 200


@main.route('/evidence/<int:evidence_id>', methods=['DELETE'])
def delete_evidence_draft(evidence_id):
    json_payload = get_json_from_request()
    actioned_by = json_payload.get('actioned_by', None)
    deleted = delete_draft_evidence(evidence_id, actioned_by)
    if not deleted:
        abort(400, 'Evidence is not valid or not in a draft state')
    return jsonify(message="done"), 200


@main.route('/evidence/<int:evidence_id>/previous', methods=['GET'])
def get_previous_evidence_and_feedback(evidence_id):
    evidence = evidence_service.get_evidence_by_id(evidence_id)
    if not evidence:
        abort(404)
    if evidence.status not in ['assessed', 'rejected']:
        abort(404)
    evidence_data = evidence.serialize()
    if evidence_data:
        domain_criteria = domain_criteria_service.get_criteria_by_domain_id(evidence_data['domainId'])
        evidence_data['domain_criteria'] = [x.serialize() for x in domain_criteria]
        evidence_data['domain_price_maximum'] = evidence.domain.price_maximum
        feedback = evidence_assessment_service.find(evidence_id=evidence.id).one_or_none()
        if feedback:
            evidence_data['feedback'] = feedback.serialize()
            assessor = users.find(id=int(feedback.user_id)).one_or_none()
            evidence_data['assessor'] = assessor.name if assessor else ''
        evidence_data['domainName'] = evidence.domain.name
        supplier = suppliers.get_supplier_by_code(evidence.supplier_code)
        evidence_data['supplierName'] = supplier.name if supplier else ''
        try:
            evidence_data['criteriaNeeded'] = int(
                DomainCriteria(
                    domain_id=evidence_data.get('domainId', None),
                    rate=evidence_data.get('maxDailyRate', None)
                ).get_criteria_needed()
            )
        except DomainCriteriaInvalidRateException as e:
            abort(400, str(e))
    return jsonify(evidence=evidence_data), 200


@main.route('/evidence/<int:evidence_id>/approve', methods=['POST'])
def evidence_approve(evidence_id):
    json_payload = get_json_from_request()

    try:
        action = DomainApproval(
            actioned_by=json_payload.get('actioned_by', None),
            evidence_id=evidence_id
        )
        evidence_assessment = action.approve_domain()
    except DomainApprovalException as e:
        abort(400, str(e))

    try:
        evidence = evidence_service.get_evidence_by_id(evidence_id)
        if evidence:
            send_evidence_assessment_approval_notification(evidence)
    except Exception as e:
        current_app.logger.warn('Failed to send approval email for evidence id: {}, {}'.format(evidence_id, e))

    return jsonify(evidence_assessment=evidence_assessment.serialize()), 200


@main.route('/evidence/<int:evidence_id>/reject', methods=['POST'])
def evidence_reject(evidence_id):
    json_payload = get_json_from_request()

    failed_criteria = json_payload.get('failed_criteria', None)
    vfm = json_payload.get('vfm', None)

    try:
        action = DomainApproval(
            actioned_by=json_payload.get('actioned_by', None),
            evidence_id=evidence_id
        )
        evidence_assessment = action.reject_domain(failed_criteria, vfm)
    except DomainApprovalException as e:
        abort(400, str(e))

    try:
        evidence = evidence_service.get_evidence_by_id(evidence_id)
        if evidence:
            send_evidence_assessment_rejection_notification(evidence)
    except Exception as e:
        current_app.logger.warn('Failed to send rejection email for evidence id: {}, {}'.format(evidence_id, e))

    return jsonify(evidence_assessment=evidence_assessment.serialize()), 200
