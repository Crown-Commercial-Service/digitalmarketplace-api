import pendulum
from flask import jsonify, request
from flask_login import current_user, login_required
from app.auth import auth
from app.utils import get_json_from_request
from app.auth.suppliers import get_supplier, update_supplier_details
from app.models import db, ServiceType, ServiceSubType, ServiceTypePrice, Supplier, Region, SupplierFramework,\
    ServiceCategory, Framework
from app.auth.helpers import role_required, abort, parse_date
from itertools import groupby
from app.swagger import swag
from app.emails.prices import send_price_change_email
from operator import itemgetter


@auth.route('/supplier', methods=['GET'])
@login_required
@role_required('supplier')
def get_supplier_profile():
    """Return an authenticated supplier (role=supplier)
    ---
    tags:
      - supplier
    security:
      - basicAuth: []
    definitions:
      Supplier:
        type: object
        properties:
          abn:
            type: string
          address_address_line:
            type: string
          address_country:
            type: string
          address_postal_code:
            type: string
          address_state:
            type: string
          address_suburb:
            type: string
          category_name:
            type: string
          code:
            type: string
          contact_email:
            type: string
          contact_name:
            type: string
          contact_phone:
            type: string
          email:
            type: string
          id:
            type: number
          linkedin:
            type: string
          name:
            type: string
          phone:
            type: string
          regions:
            type: array
            items:
                type: object
                properties:
                  name:
                    type: string
                  state:
                    type: string
          representative:
            type: string
          summary:
            type: string
          website:
            type: string
    responses:
      200:
        description: A supplier
        type: object
        properties:
          user:
              $ref: '#/definitions/Supplier'
    """
    supplier = get_supplier(current_user.supplier_code)

    return jsonify(user=supplier.serializable), 200


@auth.route('/supplier/<int:code>', methods=['GET'])
@login_required
@role_required('buyer', 'supplier')
def get_supplier_by_code(code):
    """Return a supplier (role=[buyer,supplier])
    ---
    tags:
      - supplier
    security:
      - basicAuth: []
    parameters:
      - name: code
        in: path
        type: integer
        required: true
        default: all
    responses:
      200:
        description: A supplier
        type: object
        schema:
          $ref: '#/definitions/Supplier'
    """
    if current_user.role == 'supplier' and current_user.supplier_code != code:
        return jsonify(message="Unauthorised to view supplier"), 403

    supplier = get_supplier(code)

    return jsonify(supplier.serializable), 200


@auth.route('/supplier', methods=['POST', 'PATCH'])
@login_required
@role_required('supplier')
def update_supplier_profile():
    try:
        json_payload = get_json_from_request()
        supplier = update_supplier_details(current_user.supplier_code, **json_payload)

        return jsonify(user=supplier.serializable), 200

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
                                 email=supplier_json.get('email', None),
                                 contact=supplier_json.get('representative', None)))


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
        .distinct(Region.state, Region.name, ServiceTypePrice.supplier_code, ServiceTypePrice.service_type_id,
                  ServiceTypePrice.sub_service_id, ServiceTypePrice.region_id)\
        .order_by(Region.state, Region.name, ServiceTypePrice.supplier_code.desc(),
                  ServiceTypePrice.service_type_id.desc(), ServiceTypePrice.sub_service_id.desc(),
                  ServiceTypePrice.region_id.desc(), ServiceTypePrice.updated_at.desc())\
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
    prices = json_data.get('prices')
    results = []

    for p in prices:
        existing_price = db.session.query(ServiceTypePrice).get(p['id'])

        if existing_price is None:
            abort('Invalid price id: {}'.format(p['id']))

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
        new_price = add_price(existing_price, date_from, date_to, price)
        trailing_price = add_price(new_price, date_to.add(days=1),
                                   pendulum.Date.create(2050, 1, 1), existing_price.price)\
            if end_date else None

        results.append([x for x in [existing_price, new_price, trailing_price] if x is not None])

    db.session.commit()
    send_price_change_email(results)

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


@auth.route('/suppliers', methods=['GET'])
@login_required
@role_required('buyer')
def get_all_suppliers():
    """Return the suppliers by category (role=buyer)
    ---
    tags:
      - supplier
    security:
      - basicAuth: []
    responses:
      200:
        description: A supplier
        type: object
        properties:
          categories:
            type: array
            items:
              type: object
              properties:
                name:
                  type: string
                suppliers:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: integer
                      name:
                        type: string
    """
    suppliers = db.session.query(ServiceCategory.name.label('category_name'), Supplier.code, Supplier.name)\
        .select_from(Supplier)\
        .join(SupplierFramework, Supplier.code == SupplierFramework.supplier_code)\
        .join(Framework, SupplierFramework.framework_id == Framework.id)\
        .join(ServiceTypePrice, ServiceTypePrice.supplier_code == Supplier.code)\
        .join(ServiceType, ServiceType.id == ServiceTypePrice.service_type_id)\
        .join(ServiceCategory, ServiceCategory.id == ServiceType.category_id)\
        .group_by(ServiceCategory.name, Supplier.code, Supplier.name)\
        .order_by(ServiceCategory.name, Supplier.name)\
        .all()

    suppliers_json = [dict(category_name=s.category_name, name=s.name, code=s.code) for s in suppliers]

    result = []
    for key, group in groupby(suppliers_json, key=itemgetter('category_name')):
        result.append(dict(name=key, suppliers=list(remove('category_name', group))))

    return jsonify(categories=result), 200


def remove(key, group):
    for item in group:
        del item[key]
        yield item
