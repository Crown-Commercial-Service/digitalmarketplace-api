from flask import jsonify
from flask_login import login_required
from app.api import api
from app.api.helpers import role_required
from app.api.services.reports import brief_responses_service


@api.route('/reports/brief_response/submitted', methods=['GET'])
@login_required
@role_required('admin')
def get_submitted_brief_responses():
    """Submitted Brief Responses
    ---
    tags:
      - reports
    definitions:
      BriefResponses:
        type: object
        properties:
          brief_id:
            type: number
          supplier_code:
            type: number
          created_at:
            type: string
          day_rate:
            type: number
          brief_type:
            type: string
          brief_category:
            type: string
    responses:
      200:
        description: Submitted Brief Responses
        schema:
          $ref: '#/definitions/BriefResponses'

    """
    result = brief_responses_service.get_submitted_brief_responses()
    return jsonify({
        'items': result,
        'total': len(result)
    })
