from flask import current_app, jsonify
from app.api import api
from app.api.helpers import require_api_key_auth
from app.api.services.reports import suppliers_service
from itertools import groupby


@api.route('/reports/supplier/unassessed', methods=['GET'])
@require_api_key_auth
def get_unassessed():
    unassessed = suppliers_service.get_unassessed()
    result = []
    frontend_address = current_app.config['FRONTEND_ADDRESS']
    i = None
    case_study_urls = []
    for key, group in groupby(unassessed, lambda s: s['supplier_code']):
        case_study_urls = []
        i = None
        for g in group:
            if i is None:
                i = g
            case_study_urls.append('{}/case-study/{}'.format(frontend_address, g['case_study_id']))

        i['case_study_urls'] = case_study_urls
        del i['case_study_id']
        result.append(i)

    return jsonify(result)


@api.route('/reports/supplier/all', methods=['GET'])
@require_api_key_auth
def get_all_suppliers():
    result = suppliers_service.get_suppliers()
    return jsonify({
        'items': result,
        'total': len(result)
    })
