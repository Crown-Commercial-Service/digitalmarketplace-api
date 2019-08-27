import pendulum
from app.api import api
from flask import request, jsonify
from flask_login import login_required
from app.api.helpers import not_found
from app.api.services import domain_service, key_values_service


@api.route('/domains', methods=['GET'])
@login_required
def get_domains():
    domains = []
    for domain in domain_service.get_active_domains():
        domains.append(domain.serialize())
    return jsonify({'domains': domains})


@api.route('/domains/<int:domain_id>', methods=['GET'])
@login_required
def get_domain(domain_id):
    domain = domain_service.get_by_name_or_id(domain_id, show_legacy=False)
    if not domain:
        return not_found('Domain does not exist')

    data = domain.serialize()

    data['criteriaEnforcementCutoffDate'] = None
    key_value = key_values_service.get_by_key('criteria_enforcement_cutoff_date')
    if key_value:
        data['criteriaEnforcementCutoffDate'] = (
            pendulum.parse(key_value['data']['value'], tz='Australia/Canberra').isoformat()
        )

    return jsonify(data)
