from flask import jsonify, abort, current_app, request
from app.main import main
from app.models import db, Application, Assessment, AuditEvent, SupplierDomain, Supplier, Domain
from dmapiclient.audit import AuditTypes
from app.utils import (get_json_from_request, json_has_required_keys, validate_and_return_updater_request)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, noload
from app.jiraapi import get_marketplace_jira
from app.emails import send_assessment_requested_notification, send_assessment_rejected_notification
from app.tasks import publish_tasks


@main.route('/assessments', methods=['POST'])
def create_assessment():
    updater_json = validate_and_return_updater_request()
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['assessment'])
    data = json_payload['assessment']
    json_has_required_keys(data, ['supplier_code'])
    json_has_required_keys(data, ['domain_name'])
    supplier_code = data['supplier_code']
    updated_by = updater_json['updated_by']

    existing_assessment = db.session.query(
        Assessment
    ).join(
        SupplierDomain, Supplier, Domain
    ).filter(
        Supplier.code == supplier_code,
        Domain.name == data['domain_name'],
        Assessment.active
    ).first()

    if existing_assessment:
        send_assessment_requested_notification(existing_assessment, updated_by)
        publish_tasks.assessment.delay(
            publish_tasks.compress_assessment(existing_assessment),
            'existing',
            updated_by=updated_by
        )

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
        user=updated_by,
        data={},
        db_object=assessment
    ))

    if current_app.config['JIRA_FEATURES']:
        application = db.session.query(Application).filter(
            Application.supplier_code == supplier_code,
            Application.type == 'edit',
            Application.status == 'submitted'
        ).one_or_none()

        mj = get_marketplace_jira()
        mj.create_domain_approval_task(assessment, application)

    send_assessment_requested_notification(assessment, updater_json['updated_by'])

    publish_tasks.assessment.delay(
        publish_tasks.compress_assessment(assessment),
        'created',
        updated_by=updated_by
    )

    return jsonify(assessment=assessment.serializable), 201


@main.route('/assessments', methods=['GET'])
def list_assessments():
    assessments = db.session.query(
        Assessment
    ).options(
        joinedload(Assessment.briefs), joinedload(Assessment.supplier_domain)
    ).filter(
        Assessment.active
    ).outerjoin(
        SupplierDomain, Assessment.supplier_domain_id == SupplierDomain.id
    ).filter(
        SupplierDomain.status == 'unassessed'
    )
    result = []
    for assessment in assessments:
        row = {"id": assessment.id, "active": assessment.active, "created_at": assessment.created_at,
               "briefs": [{"id": brief.id, "title": brief.data['title'],
                           "dates": {"closing_date": str(brief.applications_closing_date)}}
                          for brief in assessment.briefs],
               'supplier_domain': {"status": assessment.supplier_domain.status,
                                   "domain": {"name": assessment.supplier_domain.domain.name},
                                   'supplier': {"name": assessment.supplier_domain.supplier.name,
                                                "code": assessment.supplier_domain.supplier.code}
                                   }
               }
        if assessment.supplier_domain.status == 'unassessed':
            result.append(row)

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
    json_payload = request.get_json(force=True)
    message = json_payload.get('message', None)

    if not message:
        message = None
    if message is not None and message.isspace():
        message = None

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
        if message is not None:
            send_assessment_rejected_notification(assessment.supplier_domain.supplier_id,
                                                  assessment.id,
                                                  assessment.supplier_domain.domain.name, message)
    except IntegrityError:
        abort(400)
    return jsonify(assessment.serializable), 200


@main.route('/assessments/supplier/<int:supplier_code>', methods=['GET'])
def get_supplier_assessments(supplier_code):
    supplier = Supplier.query.filter(
        Supplier.code == supplier_code,
        Supplier.status != 'deleted'
    ).first_or_404()
    existing_assessment = (
        SupplierDomain
        .query
        .filter(SupplierDomain.supplier_id == supplier.id)
        .options(
            joinedload('assessments'),
            joinedload('domain'),
        )
        .all()
    )

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
