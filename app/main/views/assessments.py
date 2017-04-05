from flask import jsonify, abort
from app.main import main
from app.models import db, Assessment, AuditEvent, SupplierDomain, Supplier, Domain
from dmapiclient.audit import AuditTypes
from app.utils import (get_json_from_request, json_has_required_keys)
from sqlalchemy.exc import IntegrityError


@main.route('/assessments', methods=['POST'])
def create_asessment():
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
        Domain.name == data['domain_name']
    ).first()

    if existing_assessment:
        return jsonify(assessment=existing_assessment.serializable), 201

    assessment = Assessment()
    assessment.update_from_json(json_payload['assessment'])
    db.session.add(assessment)

    db.session.add(AuditEvent(
        audit_type=AuditTypes.create_assessment,
        user='',
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
