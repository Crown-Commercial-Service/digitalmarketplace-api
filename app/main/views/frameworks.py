from flask import jsonify
from sqlalchemy.types import String
from sqlalchemy import func
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

    return str({
        'services_by_status': dict(db.session.query(
            DraftService.status, func.count(DraftService.status)
        ).group_by(
            DraftService.status
        ).filter(
            DraftService.framework_id == framework.id
        )),
        'services_by_lot': dict(db.session.query(
            lot_column, func.count(lot_column)
        ).group_by(
            lot_column
        ).filter(
            DraftService.framework_id == framework.id
        ).all()),
        'users': User.query.count(),
        'active_users': User.query.filter(User.logged_in_at > seven_days_ago).count(),
        'suppliers': Supplier.query.count(),
        'suppliers_interested': AuditEvent.query.filter(
            AuditEvent.data['frameworkSlug'].cast(String) == framework_slug,
            AuditEvent.type == 'register_framework_interest'
        ).count(),
        'suppliers_with_complete_declaration': SelectionAnswers.find_by_framework(framework_slug).count()
    })
