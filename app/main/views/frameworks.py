from flask import jsonify, abort, request
from sqlalchemy.types import String
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, orm, case
import datetime

from dmutils.audit import AuditTypes
from dmutils.config import convert_to_boolean
from .. import main
from ...models import (
    db, Framework, DraftService, User, Supplier, SupplierFramework, AuditEvent, Lot, ValidationError
)
from ...utils import get_json_from_request, json_has_required_keys, json_only_has_required_keys


@main.route('/frameworks', methods=['GET'])
def list_frameworks():
    frameworks = Framework.query.all()

    return jsonify(
        frameworks=[f.serialize() for f in frameworks]
    )


@main.route('/frameworks/<string:framework_slug>', methods=['GET'])
def get_framework(framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    return jsonify(frameworks=framework.serialize())


@main.route('/frameworks/<framework_slug>', methods=['POST'])
def update_framework(framework_slug):
    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first_or_404()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['frameworks', 'updated_by'])
    json_only_has_required_keys(json_payload['frameworks'], ['status'])

    try:
        framework.status = json_payload['frameworks']['status']
        db.session.add(framework)
        db.session.add(
            AuditEvent(
                audit_type=AuditTypes.framework_update,
                db_object=framework,
                user=json_payload['updated_by'],
                data={'update': json_payload['frameworks']})
        )
        db.session.commit()
    except (IntegrityError, ValidationError) as e:
        db.session.rollback()
        abort(400, "Validation Error: {}".format(e))

    return jsonify(frameworks=framework.serialize())


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
        (SupplierFramework.declaration['status'].cast(String) == 'complete', True)
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
                DraftService.framework_id == framework.id
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
                drafts_alias.supplier_id.isnot(None), func.count()
            ).select_from(
                Supplier
            ).join(
                SupplierFramework
            ).outerjoin(
                drafts_alias
            ).filter(
                SupplierFramework.framework_id == framework.id
            ).group_by(
                SupplierFramework.declaration['status'].cast(String), drafts_alias.supplier_id.isnot(None)
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
    ).order_by(SupplierFramework.supplier_id).all()

    supplier_ids = [supplier_framework.supplier_id for supplier_framework in supplier_frameworks]

    return jsonify(interestedSuppliers=supplier_ids)
