from flask import jsonify, abort, request, current_app
from datetime import datetime
from ...models import AuditEvent
from sqlalchemy import asc, Date, cast
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import true, false
from ...utils import pagination_links, get_valid_page_or_1
from .. import main
from ... import db, models
from dmutils.audit import AuditTypes
from dmutils.config import convert_to_boolean
from ...validation import is_valid_date, is_valid_acknowledged_state
from ...service_utils import validate_and_return_updater_request


AUDIT_OBJECT_TYPES = {
    "suppliers": models.Supplier,
    "services": models.Service,
}

AUDIT_OBJECT_ID_FIELDS = {
    "suppliers": models.Supplier.supplier_id,
    "services": models.Service.service_id,
}


@main.route('/audit-events', methods=['GET'])
def list_audits():
    page = get_valid_page_or_1()

    audits = AuditEvent.query.order_by(
        asc(AuditEvent.created_at)
    )

    audit_date = request.args.get('audit-date', None)
    if audit_date:
        if is_valid_date(audit_date):
            audits = audits.filter(
                cast(AuditEvent.created_at, Date) == audit_date
            )
        else:
            abort(400, 'invalid audit date supplied')

    audit_type = request.args.get('audit-type')
    if audit_type:
        if AuditTypes.is_valid_audit_type(audit_type):
            audits = audits.filter(
                AuditEvent.type == audit_type
            )
        else:
            abort(400, "Invalid audit type")

    acknowledged = request.args.get('acknowledged', None)
    if acknowledged and acknowledged != 'all':
        if is_valid_acknowledged_state(acknowledged):
            if convert_to_boolean(acknowledged):
                audits = audits.filter(
                    AuditEvent.acknowledged == true()
                )
            elif not convert_to_boolean(acknowledged):
                audits = audits.filter(
                    AuditEvent.acknowledged == false()
                )
        else:
            abort(400, 'invalid acknowledged state supplied')

    object_type = request.args.get('object-type')
    object_id = request.args.get('object-id')
    if object_type:
        if object_type not in AUDIT_OBJECT_TYPES:
            abort(400, 'invalid object-type supplied')
        if not object_id:
            abort(400, 'object-type cannot be provided without object-id')
        model = AUDIT_OBJECT_TYPES[object_type]
        id_field = AUDIT_OBJECT_ID_FIELDS[object_type]

        audits = audits.join(model, model.id == AuditEvent.object_id) \
                       .filter(id_field == object_id)
    elif object_id:
        abort(400, 'object-id cannot be provided without object-type')

    audits = audits.paginate(
        page=page,
        per_page=current_app.config['DM_API_SERVICES_PAGE_SIZE'],
    )

    return jsonify(
        auditEvents=[audit.serialize() for audit in audits.items],
        links=pagination_links(
            audits,
            '.list_audits',
            request.args
        )
    )


@main.route('/audit-events/<int:audit_id>/acknowledge', methods=['POST'])
def acknowledge_audit(audit_id):
    updater_json = validate_and_return_updater_request()

    audit_event = AuditEvent.query.get(audit_id)

    if audit_event is None:
        abort(404, "No audit event with this id")

    audit_event.acknowledged = True
    audit_event.acknowledged_at = datetime.utcnow()
    audit_event.acknowledged_by = updater_json['updated_by']

    try:
        db.session.add(audit_event)
        db.session.commit()

    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig)

    return jsonify(auditEvents=audit_event.serialize()), 200
