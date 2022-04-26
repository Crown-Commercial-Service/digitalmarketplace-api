from app.api import api
from flask import request, jsonify
from app.api.services import briefs
from app.api.business.brief.brief_business import get_lockout_dates


@api.route('/opportunities', methods=['GET'])
def get_opportunities():
    """Opportunities
    ---
    tags:
        - opportunities
    definitions:
        Location:
            type: string
        Opportunity:
            type: object
            properties:
                closed_at:
                    type: string
                company:
                    type: string
                id:
                    type: integer
                location:
                    type: array
                    items:
                        $ref: '#/definitions/Location'
                name:
                    type: string
                openTo:
                    type: string
                submissions:
                    type: integer
        Opportunities:
            type: object
            properties:
                opportunities:
                    type: array
                    items:
                        $ref: '#/definitions/Opportunity'
    parameters:
        - name: statusFilters
          in: query
          type: string
          required: false
          description: a comma separated list of filters
        - name: openToFilters
          in: query
          type: string
          required: false
          description: a comma separated list of filters
        - name: typeFilters
          in: query
          type: string
          required: false
          description: a comma separated list of filters
    responses:
        200:
            description: Data for the opportunities page
            schema:
                $ref: '#/definitions/Opportunities'
    """
    status_filters = request.args.get('statusFilters') or ''
    open_to_filters = request.args.get('openToFilters') or ''
    type_filters = request.args.get('typeFilters') or ''
    location_filters = request.args.get('locationFilters') or ''

    opportunities = briefs.get_briefs_by_filters(
        status=status_filters.split(','),
        open_to=open_to_filters.split(','),
        brief_type=type_filters.split(','),
        location=location_filters.split(',')
    )

    lockout_period = get_lockout_dates(formatted=True)

    return jsonify({'opportunities': opportunities, 'lockoutPeriod': lockout_period})
