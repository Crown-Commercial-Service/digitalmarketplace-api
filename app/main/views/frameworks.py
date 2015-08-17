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


@main.route('/frameworks/g-cloud-7/stats', methods=['GET'])
def get_framework_stats():

    seven_days_ago = datetime.datetime.now() + datetime.timedelta(-7)
    lot_column = DraftService.data['lot'].cast(String).label('lot')

    return str({
        'services_drafts': DraftService.query.filter(
                DraftService.status == "not-submitted"
            ).count(),
        'services_complete': DraftService.query.filter(
                DraftService.status == "submitted"
            ).count(),
        'services_by_lot': dict(db.session.query(
                lot_column, func.count(lot_column)
            ).group_by(lot_column).all()),
        'users': User.query.count(),
        'active_users': User.query.filter(User.logged_in_at > seven_days_ago).count(),
        'suppliers': Supplier.query.count(),
        'suppliers_interested': AuditEvent.query.filter(AuditEvent.type == 'register_framework_interest').count(),
        'suppliers_with_complete_declaration': SelectionAnswers.find_by_framework('g-cloud-7').count()
    })
