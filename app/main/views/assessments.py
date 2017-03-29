from flask import jsonify
from app.main import main
from app.models import db, Assessment, AuditEvent
from dmapiclient.audit import AuditTypes
from app.utils import (get_json_from_request, json_has_required_keys)


@main.route('/assessments', methods=['POST'])
def create_asessment():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['assessment'])

    assessment = Assessment()
    assessment.update_from_json(json_payload['assessment'])
    db.session.add(assessment)

    db.session.add(AuditEvent(
        audit_type=AuditTypes.create_assessment,
        user='',
        data={},
        db_object=assessment
    ))
    db.session.commit()

    return jsonify(assessment=assessment.serializable), 201


@main.route('/assessments', methods=['GET'])
def list_assessments():
    assessments = Assessment.query
    result = [_.serializable for _ in assessments]

    return jsonify(assessments=result), 200
