import pendulum
from flask import current_app, request, jsonify
from flask_login import login_required, current_user
from app.api import api
from app.api.services import prices
from app.api.helpers import role_required, is_current_supplier, parse_date, abort, is_service_current_framework
from app.swagger import swag
from app.emails.prices import send_price_change_email


@api.route('/prices/suppliers/<int:code>/services/<service_type_id>/categories/<category_id>', methods=['GET'],
           endpoint='filter_prices')
@login_required
@role_required('buyer', 'supplier')
@is_current_supplier
@is_service_current_framework
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

    supplier_prices = prices.get_prices(code, service_type_id, category_id, date)
    return jsonify(prices=supplier_prices), 200


@api.route('/prices', methods=['POST'], endpoint='update_prices')
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
    json_data = request.get_json()
    updated_prices = json_data.get('prices')
    results = []

    for p in updated_prices:
        existing_price = prices.get(p['id'])

        if existing_price is None:
            abort('Invalid price id: {}'.format(p['id']))

        if existing_price.supplier_code != current_user.supplier_code:
            abort('Supplier {} unauthorized to update price {}'.format(current_user.supplier_code, existing_price.id))

        start_date = p.get('startDate')
        end_date = p.get('endDate', '')
        price = p.get('price')
        date_from = parse_date(start_date)

        if end_date:
            date_to = parse_date(end_date)
        else:
            date_to = pendulum.Date.create(2050, 1, 1)

        if not date_from.is_future():
            abort('startDate must be in the future: {}'.format(date_from))

        if date_to < date_from:
            abort('endDate must be after startDate: {}'.format(date_to))

        if price > existing_price.service_type_price_ceiling.price:
            abort('price must be less than capPrice: {}'.format(price))

        existing_price.date_to = date_from.subtract(days=1)
        new_price = prices.add_price(existing_price, date_from, date_to, price)
        trailing_price = prices.add_price(new_price, date_to.add(days=1),
                                          pendulum.Date.create(2050, 1, 1), existing_price.price)\
            if end_date else None

        results.append([x for x in [existing_price, new_price, trailing_price] if x is not None])

    send_price_change_email(results)

    return jsonify(prices=results)
