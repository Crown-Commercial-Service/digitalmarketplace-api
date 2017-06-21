from flask import jsonify, abort, request, current_app
from datetime import datetime, timedelta
from ...models import AuditEvent
from sqlalchemy import asc, desc, Date, cast
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import true, false
from sqlalchemy.orm import class_mapper
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
}

AUDIT_OBJECT_ID_FIELDS = {
    "suppliers": models.Supplier.supplier_id,
    "services": models.Service.service_id,
    "frameworks": models.Framework.slug,
    "users": models.User.id,
    "briefs": models.Brief.id,
}


@main.route('/audit-events', methods=['GET'])
def list_audits():
    page = get_valid_page_or_1()
    try:
        per_page = int(request.args.get('per_page', current_app.config['DM_API_SERVICES_PAGE_SIZE']))
    except ValueError:
        abort(400, 'invalid page size supplied')

    earliest_for_each_object = convert_to_boolean(request.args.get('earliest_for_each_object'))

    if earliest_for_each_object:
        audits = db.session.query(AuditEvent.id)
    else:
        audits = AuditEvent.query

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

        ref_model = AUDIT_OBJECT_TYPES[object_type]
        ext_id_field = AUDIT_OBJECT_ID_FIELDS[object_type]

        audits = audits.filter(AuditEvent.object.is_type(ref_model))

        # "object_id" here is the *external* object_id
        if object_id:
            ref_object = ref_model.query.filter(
                ext_id_field == object_id
            ).first()

            if ref_object is None:
                abort(404, "Object with given object-type and object-id doesn't exist")

            # this `.identity_key_from_instance(...)[1][0]` is exactly the method used by sqlalchemy_utils' generic
            # relationship code to extract an object's pk value, so *should* be relatively stable, API-wise.
            # the `[1]` is to select the pk's *value* rather than the `Column` object and the `[0]` simply fetches
            # the first of any pk values - generic relationships are already assuming that compound pks aren't in
            # use by the target.
            ref_object_pk = class_mapper(ref_model).identity_key_from_instance(ref_object)[1][0]
            audits = audits.filter(
                AuditEvent.object_id == ref_object_pk
            )
    elif object_id:
        abort(400, 'object-id cannot be provided without object-type')

    if earliest_for_each_object:
        audits_subquery = audits.order_by(
            AuditEvent.object_type,
            AuditEvent.object_id,
            AuditEvent.created_at,
            AuditEvent.id,
        ).distinct(
            AuditEvent.object_type,
            AuditEvent.object_id,
        ).subquery()

        audits = AuditEvent.query.join(audits_subquery, audits_subquery.c.id == AuditEvent.id)

    sort_order = db.desc if convert_to_boolean(request.args.get('latest_first')) else db.asc
    audits = audits.order_by(sort_order(AuditEvent.created_at), sort_order(AuditEvent.id))

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


@main.route('/audit-events/<int:audit_id>', methods=['GET'])
def get_audit_event(audit_id):
    audit_event = AuditEvent.query.get(audit_id)
    if audit_event is None:
        abort(404, "No audit event with this id")

    return jsonify(auditEvents=audit_event.serialize()), 200
