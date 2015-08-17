from flask import jsonify
import datetime

from .. import main
from ...models import Framework, DraftService, Service, User, Supplier, SelectionAnswers


@main.route('/frameworks', methods=['GET'])
def list_frameworks():
    frameworks = Framework.query.all()

    return jsonify(
        frameworks=[f.serialize() for f in frameworks]
    )


@main.route('/frameworks/g-cloud-7/stats', methods=['GET'])
def get_framework_stats():

    seven_days_ago = datetime.datetime.now() + datetime.timedelta(-7)

    return str({
        'drafts': DraftService.query.filter(DraftService.status == "not-submitted").count(),
        'complete': DraftService.query.filter(DraftService.status == "submitted").count(),
        'users': User.query.count(),
        'active_users': User.query.filter(User.logged_in_at > seven_days_ago).count(),
        'suppliers': Supplier.query.count(),
        'suppliers_with_complete_declaration': SelectionAnswers.find_by_framework('g-cloud-7').count()
    })
