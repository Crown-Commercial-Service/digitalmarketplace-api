from datetime import datetime

from flask import jsonify, abort, request, current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import true, false, func
from sqlalchemy.orm import class_mapper
from dmapiclient.audit import AuditTypes
from dmutils.config import convert_to_boolean

from .. import main
from ... import db, models
from ...models import AuditEvent
from ...validation import is_valid_acknowledged_state
from ...utils import (
    get_json_from_request,
    get_valid_page_or_1,
    json_has_required_keys,
    paginated_result_response,
    single_result_response,
    compare_sql_datetime_with_string,
    validate_and_return_updater_request,
)

RESOURCE_NAME = "auditEvents"

AUDIT_OBJECT_TYPES = {
    "brief-responses": models.BriefResponse,
    "briefs": models.Brief,
    "draft-services": models.DraftService,
    "frameworks": models.Framework,
    "outcomes": models.Outcome,
    "services": models.Service,
    "suppliers": models.Supplier,
    "users": models.User,
}

AUDIT_OBJECT_ID_FIELDS = {
    "brief-responses": models.BriefResponse.id,
    "briefs": models.Brief.id,
    "draft-services": models.DraftService.id,
    "frameworks": models.Framework.slug,
    "outcomes": models.Outcome.external_id,
    "services": models.Service.service_id,
    "suppliers": models.Supplier.supplier_id,
    "users": models.User.id,
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
        # the rest of the filters we add will be added against a subquery which we will join back onto the main table
        # to retrieve the rest of the row. this allows the potentially expensive DISTINCT ON pass to be performed
        # against an absolutely minimal subset of rows which can probably be pulled straight from an index
        audits = db.session.query(AuditEvent.id)
    else:
        audits = AuditEvent.query

    audit_date = request.args.get('audit-date', None)
    if audit_date:
        try:
            filter_test = compare_sql_datetime_with_string(AuditEvent.created_at, audit_date)
        except ValueError:
            abort(400, 'invalid audit date supplied')

        audits = audits.filter(filter_test)

    audit_type = request.args.get('audit-type')
    if audit_type:
        if AuditTypes.is_valid_audit_type(audit_type):
            audits = audits.filter(
                AuditEvent.type == audit_type
            )
        else:
            abort(400, "Invalid audit type")

    user = request.args.get('user')
    if user:
        audits = audits.filter(
            AuditEvent.user == user
        )

    # note in the following that even though the supplier and draft ids *are* integers, we're doing the searches as
    # strings because of the postgres static type system's awkwardness with json types. we first let args.get normalize
    # them into actual integers though

    data_supplier_id = request.args.get('data-supplier-id', type=int)
    if data_supplier_id:
        # This filter relies on index `idx_audit_events_data_supplier_id`. See `app..models.main` for its definition.
        audits = audits.filter(
            func.coalesce(
                AuditEvent.data['supplierId'].astext,
                AuditEvent.data['supplier_id'].astext,
            ) == str(data_supplier_id)
        )

    data_draft_service_id = request.args.get('data-draft-service-id', type=int)
    if data_draft_service_id:
        # This filter relies on index `idx_audit_events_data_draft_id`. See `app..models.main` for its definition.
        audits = audits.filter(
            AuditEvent.data['draftId'].astext == str(data_draft_service_id)
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
        if not (
            acknowledged and
            convert_to_boolean(acknowledged) is False and
            audit_type == "update_service" and
            object_type == "services"
        ):
            current_app.logger.warning(
                "earliest_for_each_object option currently intended for use on acknowledged update_service events. "
                "If use with any other events is to be regular, the scope of the corresponding partial index "
                "should be expanded to cover it."
            )
        # we need to join the built-up subquery back onto the AuditEvent table to retrieve the rest of the row
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
    sort_by = getattr(AuditEvent, request.args.get('sort_by', 'created_at'))
    audits = audits.order_by(sort_order(sort_by), sort_order(AuditEvent.id))

    return paginated_result_response(
        result_name=RESOURCE_NAME,
        results_query=audits,
        page=page,
        per_page=per_page,
        endpoint='.list_audits',
        request_args=request.args
    ), 200


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

    return single_result_response(RESOURCE_NAME, audit_event), 201


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
        abort(400, format(e))

    return single_result_response(RESOURCE_NAME, audit_event), 200


# this is a "view without a route" for at the moment - it is used as an "inner" view implementation for the service
# updates acknowledgement view
def acknowledge_including_previous(
    audit_id,
    restrict_object_id=None,
    restrict_object_type=None,
    restrict_audit_type=None,
):
    updater_json = validate_and_return_updater_request()

    audit_event_query = db.session.query(AuditEvent)
    if restrict_object_id is not None:
        audit_event_query = audit_event_query.filter(AuditEvent.object_id == restrict_object_id)
    if restrict_object_type is not None:
        audit_event_query = audit_event_query.filter(AuditEvent.object.is_type(restrict_object_type))
    if restrict_audit_type is not None:
        audit_event_query = audit_event_query.filter(AuditEvent.type == restrict_audit_type)

    audit_event = audit_event_query.filter(AuditEvent.id == audit_id).one_or_none()
    if audit_event is None:
        abort(404, "No suitable audit event with this id")

    result = db.session.execute(AuditEvent.__table__.update().returning(
        AuditEvent.id
    ).where(db.and_(
        AuditEvent.object_id == audit_event.object_id,
        AuditEvent.object.is_type(type(audit_event.object)),
        AuditEvent.type == audit_event.type,
        AuditEvent.acknowledged == db.false(),
        # ugly, but this just implements the same "id tie breaker" behaviour for created_at-equal events as the
        # ordering we use in list_audits. this way there is some consistency between the two views as to what events
        # are considered "previous" in such cases. we could use postgres composite types to express this far more
        # neatly, but i can't get sqlalchemy to work with anonymous composite types.
        db.or_(
            AuditEvent.created_at < audit_event.created_at,
            db.and_(
                AuditEvent.created_at == audit_event.created_at,
                AuditEvent.id <= audit_event.id,
            ),
        ),
    )).values(
        acknowledged=db.true(),
        acknowledged_at=datetime.utcnow(),
        acknowledged_by=updater_json['updated_by'],
    )).fetchall()
    db.session.expire_all()

    try:
        db.session.commit()

    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    # returning the list of affected ids, each one in its own dict seems the most rest-ful way (but least memory
    # efficient - well spotted) of returning this information. you would think of these as the most abbreviated
    # serializations of audit events possible.
    return jsonify(auditEvents=[{"id": audit_event_id} for (audit_event_id,) in result]), 200


@main.route('/audit-events/<int:audit_id>', methods=['GET'])
def get_audit_event(audit_id):
    audit_event = AuditEvent.query.get(audit_id)
    if audit_event is None:
        abort(404, "No audit event with this id")

    return single_result_response(RESOURCE_NAME, audit_event), 200
