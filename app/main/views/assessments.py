from flask import jsonify, abort, current_app
from app.main import main
from app.models import db, Assessment, AuditEvent, SupplierDomain, Supplier, Domain
from dmapiclient.audit import AuditTypes
from app.utils import (get_json_from_request, json_has_required_keys, validate_and_return_updater_request)
from sqlalchemy.exc import IntegrityError
from app.jiraapi import get_marketplace_jira
from app.emails import send_assessment_rejected_notification
import json


@main.route('/assessments', methods=['POST'])
def create_assessment():
    updater_json = validate_and_return_updater_request()
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['assessment'])
    data = json_payload['assessment']
    json_has_required_keys(data, ['supplier_code'])
    json_has_required_keys(data, ['domain_name'])

    existing_assessment = db.session.query(
        Assessment
    ).join(
        SupplierDomain, Supplier, Domain
    ).filter(
        Supplier.code == data['supplier_code'],
        Domain.name == data['domain_name'],
        Assessment.active
    ).first()

    if existing_assessment:
        return jsonify(assessment=existing_assessment.serializable), 201

    assessment = Assessment()
    assessment.update_from_json(json_payload['assessment'])
    db.session.add(assessment)

    try:
        db.session.commit()
    except IntegrityError:
        abort(400)

    db.session.add(AuditEvent(
        audit_type=AuditTypes.create_assessment,
        user=updater_json['updated_by'],
        data={},
        db_object=assessment
    ))

    if current_app.config['JIRA_FEATURES']:
        mj = get_marketplace_jira()
        mj.create_domain_approval_task(assessment)

    return jsonify(assessment=assessment.serializable), 201


@main.route('/assessments', methods=['GET'])
def list_assessments():
    assessments = db.session.query(
        Assessment
    ).join(
        SupplierDomain
    ).filter(
        SupplierDomain.status == 'unassessed'
    )
    result = [_.serializable for _ in assessments]

    return jsonify(assessments=result), 200


@main.route('/assessments/<int:id>', methods=['GET'])
def get_assessment(id):
    assessment = Assessment.query.get(id)
    if assessment is None:
        return abort(404)

    return jsonify(assessment.serializable), 200


@main.route('/assessments/<int:id>/reject', methods=['POST'])
def reject_assessment(id):
    updater_json = validate_and_return_updater_request()

    assessment = Assessment.query.get(id)
    if assessment is None:
        return abort(404)

    assessment.active = False
    db.session.add(assessment)

    db.session.add(AuditEvent(
        audit_type=AuditTypes.reject_assessment,
        user=updater_json['updated_by'],
        data={},
        db_object=assessment
    ))

    try:
        db.session.commit()
        send_assessment_rejected_notification(assessment.supplier_domain.supplier_id,
                                              assessment.supplier_domain.domain_id)
    except IntegrityError:
        abort(400)
    return jsonify(assessment.serializable), 200


@main.route('/assessments/supplier/<int:supplier_code>', methods=['GET'])
def get_supplier_assessments(supplier_code):
    supplier = Supplier.query.filter(
        Supplier.code == supplier_code,
        Supplier.status != 'deleted'
    ).first_or_404()
    existing_assessment = SupplierDomain.query.filter(SupplierDomain.supplier_id == supplier.id).all()

    assessments = {'assessed': [], 'unassessed': [], 'briefs': []}

    for row in existing_assessment:
        for assessment in row.assessments:
            if assessment.active:
                if assessment.briefs:
                    assessments['briefs'] = list(set(assessments['briefs'] + ([x.id for x in assessment.briefs])))
                if row.status == 'assessed':
                    assessments['assessed'].append(row.domain.name)
                if row.status == 'unassessed':
                    assessments['unassessed'].append(row.domain.name)

    return jsonify(assessments), 200
