from flask import jsonify, abort
from app.main import main
from app.models import db, Assessment, AuditEvent, SupplierDomain, Supplier, Domain
from dmapiclient.audit import AuditTypes
from app.utils import (get_json_from_request, json_has_required_keys, validate_and_return_updater_request)
from sqlalchemy.exc import IntegrityError


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

    db.session.add(AuditEvent(
        audit_type=AuditTypes.create_assessment,
        user=updater_json['updated_by'],
        data={},
        db_object=assessment
    ))

    try:
        db.session.commit()
    except IntegrityError:
        abort(400)

    return jsonify(assessment=assessment.serializable), 201


@main.route('/assessments', methods=['GET'])
def list_assessments():
    assessments = Assessment.query
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
    except IntegrityError:
        abort(400)
    return jsonify(assessment.serializable), 200
