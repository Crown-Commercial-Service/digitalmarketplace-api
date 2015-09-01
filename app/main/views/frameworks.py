from flask import jsonify, abort
from sqlalchemy.types import String
from sqlalchemy import func, orm
import datetime

from .. import main
from ...models import db, Framework, DraftService, User, Supplier, SelectionAnswers, AuditEvent


@main.route('/frameworks', methods=['GET'])
def list_frameworks():
    frameworks = Framework.query.all()

    return jsonify(
        frameworks=[f.serialize() for f in frameworks]
    )


@main.route('/frameworks/<string:framework_slug>/stats', methods=['GET'])
def get_framework_stats(framework_slug):

    framework = Framework.query.filter(
        Framework.slug == framework_slug
    ).first()

    if not framework:
        abort(404, "'{}' is not a framework".format(framework.slug))

    seven_days_ago = datetime.datetime.utcnow() + datetime.timedelta(-7)

    lot_column = DraftService.data['lot'].cast(String).label('lot')

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

    return jsonify({
        'services': label_columns(
            ['lot', 'status', 'declaration_made', 'count'],
            db.session.query(
                lot_column, DraftService.status, SelectionAnswers.framework_id.isnot(None), func.count()
            ).outerjoin(
                SelectionAnswers, DraftService.supplier_id == SelectionAnswers.supplier_id
            ).group_by(
                DraftService.status, lot_column, SelectionAnswers.framework_id
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
                SelectionAnswers.question_answers['status'].cast(String),
                drafts_alias.supplier_id.isnot(None), func.count()
            ).select_from(
                Supplier
            ).outerjoin(
                AuditEvent, AuditEvent.object_id == Supplier.id
            ).outerjoin(
                SelectionAnswers
            ).outerjoin(
                drafts_alias
            ).filter(
                AuditEvent.object_type == 'Supplier',
                AuditEvent.type == 'register_framework_interest'
            ).group_by(
                SelectionAnswers.question_answers['status'].cast(String), drafts_alias.supplier_id.isnot(None)
            ).all()
        )
    })
