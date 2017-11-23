import pendulum
from flask import current_app, request
from flask_login import login_required
from app.auth import auth
from app.auth.prices import get_prices, update_prices
from app.auth.helpers import role_required, is_current_supplier, parse_date
from app.swagger import swag


@auth.route('/prices/suppliers/<int:code>/services/<service_type_id>/categories/<category_id>', methods=['GET'],
            endpoint='filter_prices')
@login_required
@role_required('buyer', 'supplier')
@is_current_supplier
def filter(code, service_type_id, category_id):
    """Filter prices (role=buyer,supplier)
    ---
    tags:
      - prices
    security:
      - basicAuth: []
    parameters:
      - name: code
        in: path
        type: integer
        required: true
        default: all
      - name: service_type_id
        in: path
        type: integer
        required: true
        default: all
      - name: category_id
        in: path
        type: integer
        required: true
        default: all
      - name: date
        in: query
        type: string
        required: false
        default: all
    definitions:
      SupplierPrices:
        type: array
        items:
          $ref: '#/definitions/SupplierPrice'
      SupplierPrice:
        type: object
        properties:
          id:
            type: integer
          name:
            type: string
          region:
            type: object
            properties:
              state:
                type: string
              name:
                type: string
          price:
            type: string
          startDate:
            type: string
          endDate:
            type: string
    responses:
      200:
        description: A list of prices
        schema:
          $ref: '#/definitions/SupplierPrices'
    """
    date = request.args.get('date', None)
    if not date:
        date = pendulum.today(current_app.config['DEADLINES_TZ_NAME']).date()
    else:
        date = parse_date(date)
    return get_prices(code, service_type_id, category_id, date)


@auth.route('/prices', methods=['POST'], endpoint='update_prices')
@login_required
@role_required('supplier')
@swag.validate('PriceUpdates')
def update():
    """Update prices (role=supplier)
    ---
    tags:
      - prices
    security:
      - basicAuth: []
    consumes:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          id: PriceUpdates
          required:
            - prices
          properties:
            prices:
              type: array
              items:
                type: object
                required:
                  - id
                  - price
                  - startDate
                properties:
                  id:
                    type: integer
                  price:
                    type: number
                    minimum: 1
                  startDate:
                    type: string
                  endDate:
                    type: string
    responses:
      200:
        description: An updated price
        schema:
          properties:
            prices:
              type: array
              items:
                $ref: '#/definitions/SupplierPrice'
    """
    return update_prices()
