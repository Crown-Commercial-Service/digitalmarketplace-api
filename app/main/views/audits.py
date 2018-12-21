from flask import jsonify, abort, request, current_app
from datetime import datetime, timedelta
from ...models import AuditEvent
from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import true, false
from ...utils import pagination_links, get_valid_page_or_1
from .. import main
from ... import db, models
from dmapiclient.audit import AuditTypes
from dmutils.config import convert_to_boolean
from dmutils.formats import DATE_FORMAT
from ...validation import is_valid_date, is_valid_acknowledged_state
from ...utils import get_json_from_request, json_has_required_keys, validate_and_return_updater_request


AUDIT_OBJECT_TYPES = {
    "suppliers": models.Supplier,
    "services": models.Service,
    "frameworks": models.Framework,
    "users": models.User,
    "briefs": models.Brief,
    "applications": models.Application,
    "supplier_domains": models.SupplierDomain
}

AUDIT_OBJECT_ID_FIELDS = {
    "suppliers": models.Supplier.code,
    "services": models.Service.service_id,
    "frameworks": models.Framework.slug,
    "users": models.User.id,
    "briefs": models.Brief.id,
    "applications": models.Application.id,
    "supplier_domains": models.SupplierDomain.id
}


@main.route('/audit-events', methods=['GET'])
def list_audits():
    page = get_valid_page_or_1()
    try:
        per_page = int(request.args.get('per_page', current_app.config['DM_API_SERVICES_PAGE_SIZE']))
    except ValueError:
        abort(400, 'invalid page size supplied')

    audits = AuditEvent.query.order_by(
        desc(AuditEvent.created_at)
        if convert_to_boolean(request.args.get('latest_first'))
        else asc(AuditEvent.created_at)
    )

    audit_date = request.args.get('audit-date', None)
    if audit_date:
        if is_valid_date(audit_date):
            audit_datetime = datetime.strptime(audit_date, DATE_FORMAT)
            audits = audits.filter(
                AuditEvent.created_at.between(audit_datetime, audit_datetime + timedelta(days=1))
            )
        else:
            abort(400, 'invalid audit date supplied')

    audit_type = request.args.get('audit-type')
    if audit_type:
        audits = audits.filter(
            AuditEvent.type == audit_type
        )

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

        ref_object = model.query.filter(
            id_field == object_id
        ).first()

        if ref_object is None:
            abort(404, "Object with given object-type and object-id doesn't exist")

        audits = audits.filter(AuditEvent.object == ref_object)

    elif object_id:
        abort(400, 'object-id cannot be provided without object-type')

    audits = audits.paginate(
        page=page,
        per_page=per_page
    )

    return jsonify(
        auditEvents=[audit.serialize() for audit in audits.items],
        links=pagination_links(
            audits,
            '.list_audits',
            request.args
        )
    )


@main.route('/audit-events', methods=['POST'])
def create_audit_event():
    json_payload = get_json_from_request()  # TODO test
    json_has_required_keys(json_payload, ['auditEvents'])  # TODO test
    audit_event_data = json_payload['auditEvents']
    json_has_required_keys(audit_event_data, ["type", "data"])

    if 'objectType' not in audit_event_data:
        if 'objectId' in audit_event_data:
            abort(400, "object ID cannot be provided without an object type")
        db_object = None
    else:
        if audit_event_data['objectType'] not in AUDIT_OBJECT_TYPES:
            abort(400, "invalid object type supplied")
        if 'objectId' not in audit_event_data:
            abort(400, "object type cannot be provided without an object ID")
        model = AUDIT_OBJECT_TYPES[audit_event_data['objectType']]
        id_field = AUDIT_OBJECT_ID_FIELDS[audit_event_data['objectType']]
        db_objects = model.query.filter(
            id_field == audit_event_data['objectId']
        ).all()
        if len(db_objects) != 1:
            abort(400, "referenced object does not exist")
        else:
            db_object = db_objects[0]

    if not AuditTypes.is_valid_audit_type(audit_event_data['type']):
        abort(400, "invalid audit type supplied")

    audit_event = AuditEvent(
        audit_type=AuditTypes[audit_event_data['type']],
        user=audit_event_data.get('user'),
        data=audit_event_data['data'],
        db_object=db_object)

    db.session.add(audit_event)
    db.session.commit()

    return jsonify(auditEvents=audit_event.serialize()), 201


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
