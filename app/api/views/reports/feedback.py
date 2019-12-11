from flask import jsonify
from app.api import api
from app.api.helpers import require_api_key_auth
from app.api.services.reports import feedback_service


@api.route('/reports/feedback/all', methods=['GET'])
@require_api_key_auth
def get_all_feedback():
    result = feedback_service.get_all_feedback()
    return jsonify({
        'items': result,
        'total': len(result)
    })
