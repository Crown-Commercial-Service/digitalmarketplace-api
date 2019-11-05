from flask import jsonify
from app.api import api
from app.api.helpers import require_api_key_auth
from app.api.services.reports import agencies_service


@api.route('/reports/agency/all', methods=['GET'])
@require_api_key_auth
def get_agencies():
    result = agencies_service.get_agencies()
    return jsonify({
        'items': result,
        'total': len(result)
    })
