from app.api import api
from flask import request, jsonify, current_app
from flask_login import current_user, login_required
from app.api.helpers import not_found, role_required, abort, exception_logger
from app.api.services import (
    evidence_service, evidence_assessment_service, domain_service, suppliers, briefs, assessments,
    domain_criteria_service
)
from app.api.business.validators import EvidenceDataValidator
from app.api.business.domain_criteria import DomainCriteria
from app.api.business.evidence_business import get_domain_and_evidence_data
from app.tasks.jira import create_evidence_assessment_in_jira
from app.tasks import publish_tasks
from app.emails.evidence_assessments import send_evidence_assessment_requested_notification
from ...utils import get_json_from_request


@api.route('/evidence/<int:domain_id>/<int:brief_id>', methods=['POST'])
@api.route('/evidence/<int:domain_id>', methods=['POST'])
@login_required
@role_required('supplier')
def create_evidence(domain_id, brief_id=None):
    """Create evidence (role=supplier)
    ---
    tags:
        - evidence
    definitions:
        EvidenceCreated:
            type: object
            properties:
                id:
                    type: number
                domain_id:
                    type: number
                supplier_code:
                    type: number
    responses:
        200:
            description: Evidence created successfully.
            schema:
                $ref: '#/definitions/EvidenceCreated'
        400:
            description: Bad request.
        403:
            description: Unauthorised to create evidence.
        500:
            description: Unexpected error.
    """
    domain = domain_service.get_by_name_or_id(domain_id, show_legacy=False)
    if not domain:
        abort('Unknown domain id')

    supplier = suppliers.get_supplier_by_code(current_user.supplier_code)
    if supplier.data.get('recruiter', '') == 'yes':
        abort('Assessment can\'t be started against a recruiter only supplier')

    existing_evidence = evidence_service.get_latest_evidence_for_supplier_and_domain(
        domain_id,
        current_user.supplier_code
    )
    if domain.name in supplier.assessed_domains:
        abort('This supplier is already assessed for this domain')

    open_assessment = assessments.get_open_assessments(
        domain_id=domain_id,
        supplier_code=current_user.supplier_code
    )
    if open_assessment or (existing_evidence and existing_evidence.status in ['draft', 'submitted']):
        abort(
            'This supplier already has a draft assessment or is awaiting assessment for this domain'
        )

    if brief_id:
        brief = briefs.find(id=brief_id).one_or_none()
        if not brief or brief.status != 'live':
            abort('Brief id does not exist or is not open for responses')

    try:
        data = {}

        if existing_evidence and existing_evidence.status == 'rejected':
            data = existing_evidence.data.copy()
        else:
            # does this supplier already have a max price for this domain set? if so, pre-populate
            current_max_price = suppliers.get_supplier_max_price_for_domain(current_user.supplier_code, domain.name)
            if current_max_price:
                data['maxDailyRate'] = int(current_max_price)

        evidence = evidence_service.create_evidence(
            domain_id,
            current_user.supplier_code,
            current_user.id,
            brief_id=brief_id,
            data=data
        )

    except Exception as e:
        rollbar.report_exc_info()
        abort(e.message)

    publish_tasks.evidence.delay(
        publish_tasks.compress_evidence(evidence),
        'created',
        name=current_user.name,
        domain=domain.name,
        supplier_code=current_user.supplier_code
    )

    return jsonify(evidence.serialize())


@api.route('/evidence/<int:evidence_id>', methods=['GET'])
@login_required
@role_required('supplier')
def get_evidence(evidence_id):
    evidence = evidence_service.get_evidence_by_id(evidence_id)
    if not evidence or current_user.supplier_code != evidence.supplier_code:
        not_found("No evidence for id '%s' found" % (evidence_id))

    data = evidence.serialize()
    data['failed_criteria'] = {}
    data['previous_evidence_id'] = None
    previous_evidence = evidence_service.get_previous_submitted_evidence_for_supplier_and_domain(
        evidence.id,
        evidence.domain.id,
        current_user.supplier_code
    )
    if previous_evidence and previous_evidence.status == 'rejected':
        previous_assessment = evidence_assessment_service.get_assessment_for_rejected_evidence(previous_evidence.id)
        if previous_assessment:
            data['failed_criteria'] = previous_assessment.data.get('failed_criteria', {})
            data['previous_evidence_id'] = previous_evidence.id

    return jsonify(data)


@api.route('/evidence/<int:evidence_id>/view', methods=['GET'])
@exception_logger
@login_required
@role_required('supplier')
def get_domain_and_evidence(evidence_id):
    data = get_domain_and_evidence_data(evidence_id)
    return jsonify(data)


@api.route('/evidence/<int:evidence_id>/feedback', methods=['GET'])
@login_required
@role_required('supplier')
def get_evidence_feedback(evidence_id):
    evidence = evidence_service.get_evidence_by_id(evidence_id)
    if not evidence or current_user.supplier_code != evidence.supplier_code:
        not_found("No evidence for id '%s' found" % (evidence_id))
    if not evidence.status == 'rejected':
        abort('Only rejected submissions can contain feedback')
    evidence_assessment = evidence_assessment_service.get_assessment_for_rejected_evidence(evidence_id)
    if not evidence_assessment:
        abort('Failed to get the evidence assessment')

    try:
        domain_criteria = DomainCriteria(domain_id=evidence.domain.id, rate=evidence.data.get('maxDailyRate', None))
        criteria_needed = domain_criteria.get_criteria_needed()
    except Exception as e:
        abort(str(e))

    criteria_from_domain = {}
    domain_criteria = domain_criteria_service.get_criteria_by_domain_id(evidence.domain.id)
    for criteria in domain_criteria:
        criteria_from_domain[str(criteria.id)] = {
            "name": criteria.name,
            "essential": criteria.essential
        }

    criteria = {}
    failed_criteria = evidence_assessment.data.get('failed_criteria', {})
    vfm = evidence_assessment.data.get('vfm', None)
    for criteria_id, criteria_response in evidence.get_criteria_responses().iteritems():
        has_feedback = True if criteria_id in failed_criteria.keys() else False
        criteria[criteria_id] = {
            "response": criteria_response,
            "name": criteria_from_domain[criteria_id]['name'] if criteria_id in criteria_from_domain else '',
            "essential": (
                criteria_from_domain[criteria_id]['essential'] if criteria_id in criteria_from_domain else False
            ),
            "has_feedback": has_feedback,
            "assessment": failed_criteria[criteria_id] if has_feedback else {}
        }

    current_evidence = evidence_service.get_latest_evidence_for_supplier_and_domain(
        evidence.domain.id,
        current_user.supplier_code
    )

    data = {
        'domain_id': evidence.domain.id,
        'domain_name': evidence.domain.name,
        'criteria': criteria,
        'criteria_needed': criteria_needed,
        'current_evidence_id': current_evidence.id if current_evidence.status == 'draft' else None,
        'vfm': vfm
    }

    return jsonify(data)


@api.route('/evidence/<int:evidence_id>', methods=['PATCH'])
@login_required
@role_required('supplier')
def update_evidence(evidence_id):
    evidence = evidence_service.get_evidence_by_id(evidence_id)
    if not evidence or current_user.supplier_code != evidence.supplier_code:
        not_found("No evidence for id '%s' found" % (evidence_id))

    if evidence.status != 'draft':
        abort('Only draft submissions can be edited')

    data = get_json_from_request()

    if 'created_at' in data:
        del data['created_at']

    publish = False
    if 'publish' in data and data['publish']:
        del data['publish']
        publish = True

    if 'maxDailyRate' in data:
        try:
            data['maxDailyRate'] = int(data['maxDailyRate'])
        except ValueError as e:
            data['maxDailyRate'] = 0

    # Validate the evidence request data
    errors = EvidenceDataValidator(data, evidence=evidence).validate(publish=publish)
    if len(errors) > 0:
            abort(', '.join(errors))

    if publish:
        evidence.submit()
        if current_app.config['JIRA_FEATURES']:
            create_evidence_assessment_in_jira.delay(evidence_id)
        try:
            send_evidence_assessment_requested_notification(evidence_id, evidence.domain_id, current_user.email_address)
        except Exception as e:
            current_app.logger.warn(
                'Failed to send requested assessment email for evidence id: {}, {}'.format(evidence_id, e)
            )

    evidence.data = data
    evidence_service.save_evidence(evidence)

    try:
        publish_tasks.evidence.delay(
            publish_tasks.compress_evidence(evidence),
            'updated',
            name=current_user.name,
            domain=evidence.domain.name,
            supplier_code=current_user.supplier_code
        )

        if publish:
            publish_tasks.evidence.delay(
                publish_tasks.compress_evidence(evidence),
                'submitted',
                name=current_user.name,
                domain=evidence.domain.name,
                supplier_code=current_user.supplier_code
            )
    except Exception as e:
        pass

    return jsonify(evidence.serialize())
