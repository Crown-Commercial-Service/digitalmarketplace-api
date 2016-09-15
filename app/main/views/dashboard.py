from operator import itemgetter

from dmutils.filters import timesince
from flask import jsonify
from sqlalchemy import desc

from .. import main
from ...models import (Brief, Supplier, ServiceRole, PriceSchedule, User)


@main.route('/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    # workaround as 'Brief.withdrawn_at == None' gives pep8 error
    brief_query = Brief.query.filter(Brief.withdrawn_at.is_(None), Brief.published_at.isnot(None))
    all_briefs = brief_query.order_by(desc(Brief.published_at)).all()

    briefs = {
        'open_to_all': brief_query.filter(Brief.data['sellerSelector'].astext == 'allSellers').count(),

        'open_to_selected': brief_query.filter(Brief.data['sellerSelector'].astext == 'someSellers').count(),

        'open_to_one': brief_query.filter(Brief.data['sellerSelector'].astext == 'oneSellers').count(),

        'recent_brief_time_since': (timesince(all_briefs[0].published_at)) if all_briefs else ''
    }

    suppliers = {
        "total": Supplier.query.count()
    }

    buyers = {
        'total': User.query.filter(User.active.is_(True), User.role == 'buyer').count()
    }

    top_roles = []
    all_roles = ServiceRole.query.all()

    for role in all_roles:
        name = role.name.replace('Junior', '').replace('Senior', '').strip()
        count = PriceSchedule.query.filter(PriceSchedule.service_role_id == role.id).count()
        dict_exist = False
        for top_role in top_roles:
            if top_role['name'] == name:
                top_role['count'] += count
                dict_exist = True

        if not dict_exist:
            role_data = {
                'name': name,
                'count': count
            }
            top_roles.append(role_data)

    roles = {
        'top_roles': sorted(top_roles, key=itemgetter('count'), reverse=True)
    }

    stats = {
        'briefs': briefs,
        'suppliers': suppliers,
        'buyers': buyers,
        'roles': roles,
    }

    return jsonify(stats=stats)
