from flask import jsonify
from app.api import api
from app.api.helpers import require_api_key_auth
from app.api.services.reports import brief_responses_service


@api.route('/reports/brief_response/submitted', methods=['GET'])
@require_api_key_auth
def get_submitted_brief_responses():
    result = brief_responses_service.get_submitted_brief_responses()
    return jsonify({
        'items': result,
        'total': len(result)
    })
