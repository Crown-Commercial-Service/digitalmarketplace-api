from flask import jsonify
from flask_login import login_required
from app.auth import auth
from app.models import db, Region
from itertools import groupby
from operator import itemgetter
from app.auth.helpers import role_required


@auth.route('/regions', methods=['GET'], endpoint='get_all_regions')
@login_required
@role_required('buyer')
def get_all():
    """All regions (role=buyer)
    ---
    tags:
      - regions
    security:
      - basicAuth: []
    definitions:
      Regions:
        properties:
          regions:
            type: array
            items:
              $ref: '#/definitions/Region'
      Region:
        type: object
        properties:
          name:
            type: string
          subRegions:
            type: array
            items:
              $ref: '#/definitions/SubRegion'
      SubRegion:
        type: object
        properties:
          id:
            type: integer
          name:
            type: string
    responses:
      200:
        description: A list of regions
        schema:
          $ref: '#/definitions/Regions'
    """
    regions_data = db.session.query(Region).order_by(Region.state).all()
    regions = [_.serializable for _ in regions_data]

    result = []
    for key, group in groupby(regions, key=itemgetter('state')):
        result.append(dict(name=key, subRegions=list(dict(id=s['id'], name=s['name']) for s in group)))

    return jsonify(regions=result), 200
