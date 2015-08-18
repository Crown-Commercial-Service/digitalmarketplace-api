from flask import jsonify
from sqlalchemy.types import String, Boolean
from sqlalchemy import func, or_
import datetime

from .. import main
from ...models import db, Framework, DraftService, Service, User, Supplier, SelectionAnswers, AuditEvent


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

    def label_columns(labels, query):
        return [dict(zip(labels, item)) for item in query]

    return jsonify({
        'services': label_columns(
            ['status', 'lot', 'declaration_made', 'count'],
            db.session.query(
                DraftService.status, lot_column, SelectionAnswers.framework_id.isnot(None), func.count()
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
            ['has_made_declaration', 'count'],
            db.session.query(
                SelectionAnswers.framework_id.isnot(None), func.count()
            ).select_from(
                Supplier
            ).outerjoin(
                AuditEvent, AuditEvent.object_id == Supplier.id
            ).filter(
                AuditEvent.type == 'register_framework_interest'
            ).join(
                SelectionAnswers, isouter=True
            ).group_by(
                SelectionAnswers.framework_id
            ).all()
        )
    })
