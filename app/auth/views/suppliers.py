from flask import jsonify
from flask_login import current_user, login_required
from app.auth import auth
from app.utils import get_json_from_request
from app.auth.suppliers import get_supplier, update_supplier_details, valid_supplier, flatten_supplier
from app.models import db, ServiceType, ServiceSubType, ServiceTypePrice
from app.auth.helpers import role_required, format_date, format_price
from itertools import groupby


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
        schema:
          $ref: '#/definitions/SupplierServices'
    """
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

    return jsonify(services=result)


@auth.route('/supplier/services/<service_type_id>/prices', methods=['GET'])
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
    prices = db.session.query(ServiceTypePrice)\
        .filter(ServiceTypePrice.supplier_code == current_user.supplier_code,
                ServiceTypePrice.service_type_id == service_type_id,
                ServiceTypePrice.sub_service_id == category_id)\
        .all()

    return jsonify(prices=[dict(
        id=p.id,
        region=dict(state=p.region.state, name=p.region.name),
        price=format_price(p.price),
        capPrice=format_price(None if p.service_type_price_ceiling is None else p.service_type_price_ceiling.price),
        startDate=format_date(p.date_from),
        endDate=format_date(p.date_to)) for p in prices]), 200
