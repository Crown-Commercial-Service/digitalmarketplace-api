import datetime

from flask import jsonify, abort, request
from sqlalchemy import func, orm, case, text
from sqlalchemy.exc import IntegrityError, DataError
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
)
from ... import supplier_constants
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

    except IntegrityError as error:
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

    if json_framework.get('status', None) == 'pending' and framework.status != 'pending':
        # When we set a framework to pending, we want to polyfill all supplier declarations (regardless of whether
        # their application is 'complete' or not) with information from their supplier account. We have a set of
        # hardcoded keys for these values. Currently these keys don't need to mean anything outside of the API, so
        # they are defined in dm-api/app/supplier_constants. At the time this was written, it didn't seem feasible to
        # manage this query through SQLAlchemy in an efficient (i.e. 100% server-side) manner, so we are using raw SQL.

        # We pump this data into the declaration before updating the framework state, so that if for some reason the
        # framework state fails to update, when a second attempt is made the data is overwritten. We deal with the
        # theoretical scenario where a supplier has multiple ContactInformation entries by taking the first associated
        # entry and using the details from that. If we add more advanced logic in the future, this will need updating.
        statement = text(f"""
UPDATE
    supplier_frameworks
SET
    declaration = supplier_frameworks.declaration::jsonb || (
        SELECT
            row_to_json(data)
        FROM
        (
            SELECT
                suppliers.name AS "{supplier_constants.KEY_TRADING_NAME}",
                suppliers.registered_name AS "{supplier_constants.KEY_REGISTERED_NAME}",
                COALESCE(suppliers.companies_house_number,
                         suppliers.other_company_registration_number) AS "{supplier_constants.KEY_REGISTRATION_NUMBER}",
                suppliers.duns_number AS "{supplier_constants.KEY_DUNS_NUMBER}",
                suppliers.vat_number AS "{supplier_constants.KEY_VAT_NUMBER}",
                suppliers.trading_status AS "{supplier_constants.KEY_TRADING_STATUS}",
                suppliers.organisation_size AS "{supplier_constants.KEY_ORGANISATION_SIZE}",
                suppliers.registration_country AS "{supplier_constants.KEY_REGISTRATION_COUNTRY}",
                contact_information.address1 AS "{supplier_constants.KEY_REGISTRATION_BUILDING}",
                contact_information.city AS "{supplier_constants.KEY_REGISTRATION_TOWN}",
                contact_information.postcode AS "{supplier_constants.KEY_REGISTRATION_POSTCODE}"
            FROM
                suppliers
            JOIN
                contact_information ON suppliers.supplier_id = contact_information.supplier_id
            WHERE
                suppliers.supplier_id = supplier_frameworks.supplier_id
            ORDER BY contact_information.id ASC
            LIMIT 1
        ) AS data
    )::jsonb
WHERE
    supplier_frameworks.framework_id = :framework_id""")

        db.session.execute(statement, {"framework_id": framework.id})

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
