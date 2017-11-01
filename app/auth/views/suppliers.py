import pendulum
from flask import jsonify, request
from flask_login import current_user, login_required
from app.auth import auth
from app.utils import get_json_from_request
from app.auth.suppliers import get_supplier, update_supplier_details, valid_supplier, flatten_supplier
from app.models import db, ServiceType, ServiceSubType, ServiceTypePrice, Supplier, Region
from app.auth.helpers import role_required, abort
from itertools import groupby
from app.swagger import swag


@auth.route('/supplier', methods=['GET'])
@login_required
def get_supplier_profile():
    if not valid_supplier(current_user):
        return jsonify(message="Only users with role supplier can access supplier details"), 401
    else:
        supplier = get_supplier(current_user.supplier_code)
        supplier = flatten_supplier(supplier.serializable)
        return jsonify(user=supplier), 200


@auth.route('/supplier', methods=['POST', 'PATCH'])
@login_required
def update_supplier_profile():
    if not valid_supplier(current_user):
        return jsonify(message="Only users with role supplier can update supplier details"), 401

    try:
        json_payload = get_json_from_request()
        supplier = update_supplier_details(current_user.supplier_code, **json_payload)
        supplier = flatten_supplier(supplier.serializable)

        return jsonify(user=supplier), 200

    except Exception as error:
        return jsonify(message=error.message), 400


@auth.route('/supplier/services', methods=['GET'])
@login_required
@role_required('supplier')
def supplier_services():
    """Return a list of services and sub categories for the current supplier (role=supplier)
    ---
    tags:
      - supplier
    security:
      - basicAuth: []
    definitions:
      SupplierServices:
        type: object
        properties:
          services:
            type: array
            items:
              $ref: '#/definitions/SupplierService'
      SupplierService:
        type: object
        properties:
          id:
            type: integer
          name:
            type: string
          subCategories:
            type: array
            items:
              $ref: '#/definitions/SupplierCategory'
      SupplierCategory:
        type: object
        properties:
          id:
            type: integer
          name:
            type: string
    responses:
      200:
        description: A list of services with sub categories
        type: object
        properties:
          supplier:
            type:
              object
            properties:
              name:
                type: string
              abn:
                type: string
              email:
                type: string
              contact:
                type: string
          services:
            type: array
            items:
              $ref: '#/definitions/SupplierService'
    """
    supplier = db.session.query(Supplier).filter(Supplier.code == current_user.supplier_code).first()

    services = db.session\
        .query(ServiceTypePrice.service_type_id,
               ServiceType.name, ServiceTypePrice.sub_service_id, ServiceSubType.name.label('sub_service_name'))\
        .join(ServiceType, ServiceTypePrice.service_type_id == ServiceType.id)\
        .outerjoin(ServiceSubType, ServiceTypePrice.sub_service_id == ServiceSubType.id)\
        .filter(ServiceTypePrice.supplier_code == current_user.supplier_code)\
        .group_by(ServiceTypePrice.service_type_id, ServiceType.name,
                  ServiceTypePrice.sub_service_id, ServiceSubType.name)\
        .order_by(ServiceType.name)\
        .all()

    result = []
    for key, group in groupby(services, key=lambda x: dict(id=x.service_type_id, name=x.name)):
        subcategories = [dict(id=s.sub_service_id, name=s.sub_service_name) for s in group]
        result.append(dict(key, subCategories=subcategories))

    supplier_json = supplier.serializable
    return jsonify(services=result,
                   supplier=dict(name=supplier_json['name'], abn=supplier_json['abn'],
                                 email=None if 'contact_email' not in supplier_json else supplier_json['contact_email'],
                                 contact=None if 'contact_name' not in supplier_json
                                 else supplier_json['contact_name']))


@auth.route('/supplier/services/<service_type_id>/categories/<category_id>/prices', methods=['GET'])
@login_required
@role_required('supplier')
def supplier_service_prices(service_type_id, category_id=None):
    """Return a list of prices for the current supplier (role=supplier)
    ---
    tags:
      - supplier
    security:
      - basicAuth: []
    parameters:
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
    prices = db.session.query(ServiceTypePrice)\
        .join(ServiceTypePrice.region)\
        .filter(ServiceTypePrice.supplier_code == current_user.supplier_code,
                ServiceTypePrice.service_type_id == service_type_id,
                ServiceTypePrice.sub_service_id == category_id,
                ServiceTypePrice.is_current_price)\
        .order_by(Region.state, Region.name)\
        .all()

    return jsonify(prices=[p.serializable for p in prices]), 200


@auth.route('/supplier/prices', methods=['POST'])
@login_required
@role_required('supplier')
@swag.validate('PriceUpdates')
def update_supplier_price():
    """Update a price (role=supplier)
    ---
    tags:
      - supplier
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
    prices = json_data.get('prices')
    results = []

    for p in prices:
        existing_price = db.session.query(ServiceTypePrice).get(p['id'])

        if existing_price is None:
            abort('Invalid price id: {}'.format(p['id']))

        start_date = p.get('startDate')
        end_date = p.get('endDate', '')

        date_from = pendulum.parse(start_date).date()

        if end_date:
            date_to = pendulum.parse(end_date).date()
        else:
            date_to = pendulum.Date.create(2050, 1, 1)

        existing_price.date_to = date_from.subtract(days=1)
        price = add_price(existing_price, date_from, date_to, p['price'])
        results.append(existing_price)
        results.append(price)

        if end_date:
            trailing_price = add_price(price, date_to.add(days=1),
                                       pendulum.Date.create(2050, 1, 1), existing_price.price)
            results.append(trailing_price)

    db.session.commit()
    return jsonify(prices=results)


def add_price(existing_price, date_from, date_to, price):
    new_price = ServiceTypePrice(
        supplier_code=existing_price.supplier_code,
        service_type_id=existing_price.service_type_id,
        sub_service_id=existing_price.sub_service_id,
        region_id=existing_price.region.id,
        service_type_price_ceiling_id=existing_price.service_type_price_ceiling.id,
        date_from=date_from,
        date_to=date_to,
        price=price
    )

    db.session.add(new_price)
    db.session.flush()

    return new_price
