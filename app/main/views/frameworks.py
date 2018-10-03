from flask import jsonify, abort, request
from sqlalchemy.types import String
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import joinedload
from sqlalchemy import func, orm, case, cast
import datetime

from dmapiclient.audit import AuditTypes
from dmutils.config import convert_to_boolean
from .. import main
from ...models import (
    db, Framework, DraftService, User, Supplier, SupplierFramework, AuditEvent, Lot,
)
from ...utils import (
    get_json_from_request, json_has_required_keys, json_only_has_required_keys,
    validate_and_return_updater_request,
)


@main.route('/frameworks', methods=['GET'])
def list_frameworks():
    frameworks = Framework.query.all()

    return jsonify(
        frameworks=[f.serialize() for f in frameworks]
    )


@main.route("/frameworks", methods=["POST"])
def create_framework():
    updater_json = validate_and_return_updater_request()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['frameworks'])
    json_only_has_required_keys(json_payload['frameworks'], [
        "slug", "name", "framework", "status", "clarificationQuestionsOpen", "lots"
    ])

    lots = Lot.query.filter(Lot.slug.in_(json_payload["frameworks"]["lots"])).all()
    unfound_lots = set(json_payload["frameworks"]["lots"]) - set(lot.slug for lot in lots)
    if len(unfound_lots) > 0:
        abort(400, "Invalid lot slugs: {}".format(", ".join(sorted(unfound_lots))))

    try:
        framework = Framework(
            slug=json_payload["frameworks"]["slug"],
            name=json_payload["frameworks"]["name"],
            framework=json_payload["frameworks"]["framework"],
            status=json_payload["frameworks"]["status"],
            clarification_questions_open=json_payload["frameworks"]["clarificationQuestionsOpen"],
            lots=lots
        )
        db.session.add(framework)
        db.session.add(
            AuditEvent(
                audit_type=AuditTypes.create_framework,
                db_object=framework,
                user=updater_json['updated_by'],
                data={'update': json_payload['frameworks']})
        )
        db.session.commit()
    except DataError:
        db.session.rollback()
        abort(400, "Invalid framework")
    except IntegrityError:
        db.session.rollback()
        abort(400, "Slug '{}' already in use".format(json_payload["frameworks"]["slug"]))

    return jsonify(frameworks=framework.serialize())


@main.route('/frameworks/<string:framework_slug>', methods=['GET'])
def get_framework(framework_slug):
    framework = (
        Framework
        .query
        .options(
            joinedload(Framework.lots)
        )
        .filter(
            Framework.slug == framework_slug
        )
        .first_or_404()
    )

    return jsonify(frameworks=framework.serialize())


@main.route('/frameworks/<framework_slug>', methods=['POST'])
def update_framework(framework_slug):
    updater_json = validate_and_return_updater_request()
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['frameworks'])
    json_only_has_required_keys(json_payload['frameworks'], ['status', 'clarificationQuestionsOpen'])

    try:
        framework.status = json_payload['frameworks']['status']
        framework.clarification_questions_open = json_payload['frameworks']['clarificationQuestionsOpen']
        db.session.add(framework)
        db.session.add(
            AuditEvent(
                audit_type=AuditTypes.framework_update,
                db_object=framework,
                user=updater_json['updated_by'],
                data={'update': json_payload['frameworks']})
        )
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Database Error: {}".format(e))

    return jsonify(frameworks=framework.serialize())


@main.route('/frameworks/<string:framework_slug>/stats', methods=['GET'])
def get_framework_stats(framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    seven_days_ago = datetime.datetime.utcnow() + datetime.timedelta(-7)

    has_completed_drafts_query = db.session.query(
        DraftService.supplier_code, func.min(DraftService.id)
    ).filter(
        DraftService.framework_id == framework.id,
        DraftService.status == 'submitted'
    ).group_by(
        DraftService.supplier_code
    ).subquery('completed_drafts')

    drafts_alias = orm.aliased(DraftService, has_completed_drafts_query)

    def label_columns(labels, query):
        return [
            dict(zip(labels, item))
            for item in sorted(query, key=lambda x: list(map(str, x)))
        ]

    is_declaration_complete = case([
        (SupplierFramework.declaration['status'].cast(String) == 'complete', True)
    ], else_=False)

    return jsonify({
        'services': label_columns(
            ['status', 'lot', 'declaration_made', 'count'],
            db.session.query(
                DraftService.status, Lot.slug, is_declaration_complete, func.count()
            ).outerjoin(
                SupplierFramework, DraftService.supplier_code == SupplierFramework.supplier_code
            ).join(
                Lot, DraftService.lot_id == Lot.id
            ).group_by(
                DraftService.status, Lot.slug, is_declaration_complete
            ).filter(
                SupplierFramework.framework_id == framework.id,
                DraftService.framework_id == framework.id,
                cast(SupplierFramework.declaration, String) != 'null'
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
                SupplierFramework.declaration['status'].cast(String),
                drafts_alias.supplier_code.isnot(None), func.count()
            ).select_from(
                Supplier
            ).join(
                SupplierFramework
            ).outerjoin(
                drafts_alias
            ).filter(
                SupplierFramework.framework_id == framework.id,
                cast(SupplierFramework.declaration, String) != 'null'
            ).group_by(
                SupplierFramework.declaration['status'].cast(String), drafts_alias.supplier_code.isnot(None)
            ).all()
        )
    })


@main.route('/frameworks/<string:framework_slug>/suppliers', methods=['GET'])
def get_framework_suppliers(framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    agreement_returned = request.args.get('agreement_returned')

    supplier_frameworks = SupplierFramework.query.filter(
        SupplierFramework.framework_id == framework.id
    )

    if agreement_returned is not None:
        if convert_to_boolean(agreement_returned):
            supplier_frameworks = supplier_frameworks.filter(
                SupplierFramework.agreement_returned_at.isnot(None)
            ).order_by(SupplierFramework.agreement_returned_at.desc())
        else:
            supplier_frameworks = supplier_frameworks.filter(
                SupplierFramework.agreement_returned_at.is_(None)
            )

    return jsonify(supplierFrameworks=[
        supplier_framework.serialize() for supplier_framework in supplier_frameworks
    ])


@main.route('/frameworks/<string:framework_slug>/interest', methods=['GET'])
def get_framework_interest(framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    supplier_frameworks = SupplierFramework.query.filter(
        SupplierFramework.framework_id == framework.id
    ).order_by(SupplierFramework.supplier_code).all()

    supplier_codes = [supplier_framework.supplier_code for supplier_framework in supplier_frameworks]

    return jsonify(interestedSuppliers=supplier_codes)
