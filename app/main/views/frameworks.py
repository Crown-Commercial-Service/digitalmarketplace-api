import datetime

from flask import jsonify, abort, request
from sqlalchemy import func, orm, case
from sqlalchemy.exc import IntegrityError, DataError, StatementError
from sqlalchemy.orm import lazyload, load_only
from dmapiclient.audit import AuditTypes
from dmutils.config import convert_to_boolean

from .. import main
from ...models import (
    AuditEvent,
    db,
    DraftService,
    Framework,
    Lot,
    Supplier,
    SupplierFramework,
    User,
    Brief,
)
from ...utils import (
    get_json_from_request,
    json_has_required_keys,
    json_only_has_required_keys,
    list_result_response,
    single_result_response,
    validate_and_return_updater_request,
)
from ...framework_utils import validate_framework_agreement_details_data, format_framework_integrity_error_message

RESOURCE_NAME = "frameworks"
FRAMEWORK_UPDATE_WHITELISTED_ATTRIBUTES_MAP = {
    'allowDeclarationReuse': 'allow_declaration_reuse',
    'applicationsCloseAtUTC': 'applications_close_at_utc',
    'intentionToAwardAtUTC': 'intention_to_award_at_utc',
    'clarificationQuestionsOpen': 'clarification_questions_open',
    'clarificationsCloseAtUTC': 'clarifications_close_at_utc',
    'clarificationsPublishAtUTC': 'clarifications_publish_at_utc',
    'frameworkAgreementDetails': 'framework_agreement_details',
    'frameworkExpiresAtUTC': 'framework_expires_at_utc',
    'frameworkLiveAtUTC': 'framework_live_at_utc',
    'status': 'status',
    'hasDirectAward': 'has_direct_award',
    'hasFurtherCompetition': 'has_further_competition',
}


@main.route('/frameworks', methods=['GET'])
def list_frameworks():
    return list_result_response(RESOURCE_NAME, Framework.query), 200


@main.route("/frameworks", methods=["POST"])
def create_framework():
    updater_json = validate_and_return_updater_request()
    json_payload = get_json_from_request()

    json_has_required_keys(json_payload, ['frameworks'])

    json_framework = json_payload['frameworks']
    json_only_has_required_keys(json_framework, [
        "slug", "name", "framework", "status", "clarificationQuestionsOpen", "lots", "hasDirectAward",
        "hasFurtherCompetition",
    ])

    lots = Lot.query.filter(Lot.slug.in_(json_framework["lots"])).all()
    unfound_lots = set(json_framework["lots"]) - set(lot.slug for lot in lots)

    if len(unfound_lots) > 0:
        abort(400, "Invalid lot slugs: {}".format(", ".join(sorted(unfound_lots))))

    try:
        framework = Framework(
            slug=json_framework["slug"],
            name=json_framework["name"],
            framework=json_framework["framework"],
            status=json_framework["status"],
            clarification_questions_open=json_framework["clarificationQuestionsOpen"],
            lots=lots,
            has_direct_award=json_framework["hasDirectAward"],
            has_further_competition=json_framework["hasFurtherCompetition"],
        )
        db.session.add(framework)
        db.session.flush()
        db.session.add(
            AuditEvent(
                audit_type=AuditTypes.create_framework,
                db_object=framework,
                user=updater_json['updated_by'],
                data={'update': json_framework})
        )
        db.session.commit()

    except DataError:
        db.session.rollback()
        abort(400, "Invalid framework")

    except StatementError as error:
        # here we catch StatementError where most views would normally catch IntegrityError - this is because this view
        # does not use e.g. a json schema for validation of the passed json structure, and so can't be certain e.g.
        # of the object types being assigned to database fields above
        db.session.rollback()
        abort(400, format_framework_integrity_error_message(error, json_framework))

    return single_result_response(RESOURCE_NAME, framework), 201


@main.route('/frameworks/<string:framework_slug>', methods=['GET'])
def get_framework(framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    return single_result_response(RESOURCE_NAME, framework), 200


@main.route('/frameworks/<string:framework_slug>', methods=['POST'])
def update_framework(framework_slug):
    updater_json = validate_and_return_updater_request()
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['frameworks'])

    json_framework = json_payload['frameworks']
    if not json_framework:
        abort(400, "Framework update expects a payload")

    invalid_keys = (set(json_framework.keys()) - set(FRAMEWORK_UPDATE_WHITELISTED_ATTRIBUTES_MAP.keys()))
    if invalid_keys:
        abort(400, "Invalid keys for framework update: '{}'".format("', '".join(invalid_keys)))

    if 'frameworkAgreementDetails' in json_framework:
        # all frameworkAgreementDetails keys must be present or the update will fail
        validate_framework_agreement_details_data(
            json_framework['frameworkAgreementDetails'],
            enforce_required=True
        )

    # We can ensure that some of the timestamps we have for a framework are accurate, as they are tied to state changes.
    status_timestamp_audit_data = {}
    if json_framework.get('clarificationQuestionsOpen') is False and framework.clarification_questions_open is True:
        framework.clarifications_close_at_utc = datetime.datetime.utcnow()
        status_timestamp_audit_data = {"clarifications_close_at_utc set": "clarification questions closed"}

    if json_framework.get('status') == 'pending' and framework.status != 'pending':
        framework.applications_close_at_utc = datetime.datetime.utcnow()
        status_timestamp_audit_data = {"applications_close_at_utc set": "framework status set to 'pending'"}
    elif json_framework.get('status') == 'live' and framework.status != 'live':
        framework.framework_live_at_utc = datetime.datetime.utcnow()
        status_timestamp_audit_data = {"framework_live_at_utc set": "framework status set to 'live'"}
    elif json_framework.get('status') == 'expired' and framework.status != 'expired':
        framework.framework_expires_at_utc = datetime.datetime.utcnow()
        status_timestamp_audit_data = {"framework_expires_at_utc set": "framework status set to 'expired'"}

    for whitelisted_key, value in FRAMEWORK_UPDATE_WHITELISTED_ATTRIBUTES_MAP.items():
        if whitelisted_key in json_framework:
            setattr(framework, value, json_framework[whitelisted_key])

    try:
        db.session.add(framework)
        db.session.add(
            AuditEvent(
                audit_type=AuditTypes.framework_update,
                db_object=framework,
                user=updater_json['updated_by'],
                data={
                    'update': json_framework,
                    'frameworkSlug': framework.slug,
                    **status_timestamp_audit_data,
                },
            )
        )
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        abort(400, format_framework_integrity_error_message(error, json_framework))

    return single_result_response(RESOURCE_NAME, framework), 200


@main.route('/frameworks/<string:framework_slug>/stats', methods=['GET'])
def get_framework_stats(framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    seven_days_ago = datetime.datetime.utcnow() + datetime.timedelta(-7)

    has_completed_drafts_query = db.session.query(
        DraftService.supplier_id, func.min(DraftService.id)
    ).filter(
        DraftService.framework_id == framework.id,
        DraftService.status == 'submitted'
    ).group_by(
        DraftService.supplier_id
    ).subquery('completed_drafts')

    drafts_alias = orm.aliased(DraftService, has_completed_drafts_query)

    def label_columns(labels, query):
        return [
            dict(zip(labels, item))
            for item in sorted(query, key=lambda x: list(map(str, x)))
        ]

    is_declaration_complete = case([
        (SupplierFramework.declaration['status'].astext == 'complete', True)
    ], else_=False)

    return jsonify({
        'services': label_columns(
            ['status', 'lot', 'declaration_made', 'count'],
            db.session.query(
                DraftService.status, Lot.slug, is_declaration_complete, func.count()
            ).outerjoin(
                SupplierFramework, DraftService.supplier_id == SupplierFramework.supplier_id
            ).join(
                Lot, DraftService.lot_id == Lot.id
            ).group_by(
                DraftService.status, Lot.slug, is_declaration_complete
            ).filter(
                SupplierFramework.framework_id == framework.id,
                DraftService.framework_id == framework.id,
                SupplierFramework.declaration.isnot(None)
            ).all()
        ),
        'supplier_users': label_columns(
            ['recent_login', 'count'],
            db.session.query(
                User.logged_in_at > seven_days_ago, func.count()
            ).filter(
                User.role == 'supplier'
            ).group_by(
                User.logged_in_at > seven_days_ago
            ).all()
        ),
        'interested_suppliers': label_columns(
            ['declaration_status', 'has_completed_services', 'count'],
            db.session.query(
                SupplierFramework.declaration['status'].astext,
                drafts_alias.supplier_id.isnot(None), func.count()
            ).select_from(
                Supplier
            ).join(
                SupplierFramework
            ).outerjoin(
                drafts_alias
            ).filter(
                SupplierFramework.framework_id == framework.id,
                SupplierFramework.declaration.isnot(None)
            ).group_by(
                SupplierFramework.declaration['status'].astext, drafts_alias.supplier_id.isnot(None)
            ).all()
        )
    }), 200


@main.route('/frameworks/<string:framework_slug>/suppliers', methods=['GET'])
def get_framework_suppliers(framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    # we're going to need an "alias" for the current_framework_agreement join
    # so that we can refer to it in later clauses
    cfa = orm.aliased(SupplierFramework._CurrentFrameworkAgreement)
    supplier_frameworks = SupplierFramework.query.outerjoin(
        cfa, SupplierFramework.current_framework_agreement
    ).options(
        orm.contains_eager(
            SupplierFramework.current_framework_agreement, alias=cfa
        )
    )
    # now we can use the alias `cfa` to refer to the joinedload that
    # SupplierFramework.current_framework_agreement would usually cause

    supplier_frameworks = supplier_frameworks.filter(
        SupplierFramework.framework_id == framework.id
    ).options(
        db.defaultload(SupplierFramework.framework).lazyload("*"),
        db.defaultload(SupplierFramework.supplier).lazyload("*"),
        db.defaultload(SupplierFramework.prefill_declaration_from_framework).lazyload("*"),
        db.lazyload(SupplierFramework.framework_agreements),
    ).order_by(
        # Listing agreements is something done for Admin only (suppliers only retrieve their individual agreements)
        # and CCS always want to work from the oldest returned date to newest, so order by ascending date
        cfa.signed_agreement_returned_at.asc().nullsfirst(),
        SupplierFramework.supplier_id,
    )

    # endpoint has evolved a bit of an oddly designed interface here in that the two filterable parameters aren't
    # really orthogonal. implementing them as such anyway for clarity.

    agreement_returned = request.args.get('agreement_returned')
    if agreement_returned is not None:
        supplier_frameworks = supplier_frameworks.filter(
            # using the not-nullable FrameworkAgreement.id as a proxy for testing row null-ness
            cfa.id.isnot(None) if convert_to_boolean(agreement_returned) else cfa.id.is_(None)
        )

    status = request.args.get('status')
    if status is not None:
        supplier_frameworks = supplier_frameworks.filter(
            cfa.status.in_(status.split(","))
        )

    with_declarations = convert_to_boolean(request.args.get("with_declarations", "true"))

    return list_result_response(
        "supplierFrameworks",
        supplier_frameworks,
        serialize_kwargs={"with_users": False, "with_declaration": with_declarations}
    ), 200


@main.route('/frameworks/<string:framework_slug>/interest', methods=['GET'])
def get_framework_interest(framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier_frameworks = SupplierFramework.query.filter(
        SupplierFramework.framework_id == framework.id
    ).options(
        db.defaultload(SupplierFramework.framework).lazyload("*"),
        db.defaultload(SupplierFramework.supplier).lazyload("*"),
        db.defaultload(SupplierFramework.prefill_declaration_from_framework).lazyload("*"),
        db.lazyload(SupplierFramework.framework_agreements),
    ).order_by(SupplierFramework.supplier_id).all()

    supplier_ids = [supplier_framework.supplier_id for supplier_framework in supplier_frameworks]

    return jsonify(interestedSuppliers=supplier_ids), 200


@main.route('/frameworks/transition-dos/<string:framework_slug>', methods=['POST'])
def transition_dos_framework(framework_slug):
    """When we transition from one DOS framework to another, there is no overlap period. One framework is expired at the
    same time the other is made live. A buyer publishes a requirement, and it will either be on one framework or the
    other. Suppliers are able to apply to an opportunity even if the framework it was published on is expired, as long
    as the brief is still open (within 1 or 2 weeks of its publication date).

    The issue is that a brief is tied to a framework at the point it is created (as a draft). If a framework is expired,
    any drafts that belong to it are no longer editable/publishable. We don't want a buyer to lose a draft.

    This endpoint will update the framework statuses, move the draft briefs belonging to that framework to the incoming
    framework, and create audit events for it all. The frameworks are commited in a separate transation before the
    briefs. This is to prevent the framework rows from being locked for any longer than necessary - they're used heavily
    by many api calls. If there are lots of briefs to update the framework rows could be locked for a while, otherwise.
    """
    updater_json = validate_and_return_updater_request()
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['expiringFramework'])

    going_live_framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).with_for_update(
        of=Framework,
    ).options(
        lazyload(Framework.lots)
    ).first_or_404()
    expiring_framework = Framework.query.filter(
        Framework.slug == json_payload['expiringFramework']
    ).with_for_update(
        of=Framework,
    ).options(
        lazyload(Framework.lots)
    ).first_or_404()

    if going_live_framework.id <= expiring_framework.id:
        abort(400, f"'going_live_framework' ID ('{going_live_framework.id}') must greater than"
              f"'expiring_framework' ID ('{expiring_framework.id}')")

    if any(f.framework != 'digital-outcomes-and-specialists' for f in (going_live_framework, expiring_framework)):
        abort(400, f"'going_live_framework' family: '{going_live_framework.framework}' and 'expiring_framework' family:"
              f" '{expiring_framework.framework}' must both be 'digital-outcomes-and-specialists'")

    if going_live_framework.status != 'standstill' or expiring_framework.status != 'live':
        abort(400, f"'going_live_framework' status ({going_live_framework.status}) must be 'standstill', and "
              f"'expiring_framework' status ({expiring_framework.status}) must be 'live'")

    framework_timestamp = datetime.datetime.utcnow()

    going_live_framework.status = 'live'
    going_live_framework.framework_live_at_utc = framework_timestamp
    expiring_framework.status = 'expired'
    expiring_framework.framework_expires_at_utc = framework_timestamp
    db.session.add_all((going_live_framework, expiring_framework))

    expired_audit = AuditEvent(
        audit_type=AuditTypes.framework_update,
        db_object=expiring_framework,
        user=updater_json['updated_by'],
        data={
            "update": {
                "status": "expired",
                "framework_expires_at_utc set": "framework status set to 'expired'"
            },
            "frameworkSlug": expiring_framework.slug,
        },
    )
    expired_audit.created_at = framework_timestamp
    db.session.add(expired_audit)

    live_audit = AuditEvent(
        audit_type=AuditTypes.framework_update,
        db_object=going_live_framework,
        user=updater_json['updated_by'],
        data={
            "update": {
                "status": "live",
                "framework_live_at_utc set": "framework status set to 'live'"
            },
            "frameworkSlug": going_live_framework.slug,
        },
    )
    live_audit.created_at = framework_timestamp
    db.session.add(live_audit)

    # Commit the frameworks to release the locks on their rows to help mitigate issues that may occur if updating the
    # briefs below takes a long time.
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        abort(400, format_framework_integrity_error_message(error, {}))

    expiring_framework_draft_briefs = Brief.query.options(
        load_only('id', 'framework_id'),
    ).filter(
        Brief.status == 'draft',
        Brief.framework_id == expiring_framework.id,
    ).with_for_update(
        of=Brief,
    ).all()

    brief_timestamp = datetime.datetime.utcnow()

    for brief in expiring_framework_draft_briefs:
        brief.framework_id = going_live_framework.id
        db.session.add(brief)
        db.session.flush()

        brief_audit = AuditEvent(
            audit_type=AuditTypes.update_brief_framework_id,
            user=updater_json['updated_by'],
            data={
                'briefId': brief.id,
                'previousFrameworkId': expiring_framework.id,
                'newFrameworkId': going_live_framework.id,
            },
            db_object=brief,
        )
        brief_audit.created_at = brief_timestamp

        db.session.add(brief_audit)

    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        abort(400, format_framework_integrity_error_message(error, {}))

    return single_result_response(RESOURCE_NAME, going_live_framework), 200
