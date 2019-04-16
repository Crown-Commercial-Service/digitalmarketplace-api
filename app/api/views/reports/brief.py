from flask import jsonify
from flask_login import login_required
from app.api import api
from app.api.helpers import role_required
from app.api.services.reports import briefs_service


@api.route('/reports/brief/published', methods=['GET'])
@login_required
@role_required('admin')
def get_published_briefs():
    """Published Brief
    ---
    tags:
      - reports
    definitions:
      Brief:
        type: object
        properties:
          id:
            type: number
          organisation:
            type: string
          published_at:
            type: string
          withdrawn_at:
            type: string
          title:
            type: string
          openTo:
            type: string
          brief_category:
            type: string
          brief_type:
            type: string
          publisher_domain:
            type: string
    responses:
      200:
        description: Published Briefs
        schema:
          $ref: '#/definitions/Brief'

    """
    result = briefs_service.get_published_briefs()
    return jsonify({
        'items': result,
        'total': len(result)
    })
