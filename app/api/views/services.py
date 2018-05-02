from flask import jsonify, current_app
from flask_login import login_required
from app.api import api
from app.models import db, Region, ServiceCategory, ServiceType, ServiceTypePrice, Supplier, ServiceSubType
from itertools import groupby
from operator import itemgetter
from app.api.helpers import role_required, is_service_current_framework
import pendulum

ALERTS = {
    'fixed': {
        'type': 'info',
        'message': 'This service is a fixed fee - inclusive of travel, assessment and report'
    },
    'hourly': {
        'type': 'warning',
        'message': 'The prices for this service are per hour and inclusive of travel costs.'
    }
}


@api.route('/services', methods=['GET'], endpoint='list_services')
@login_required
@role_required('buyer')
def get_list():
    """All services (role=buyer)
    ---
    tags:
      - services
    security:
      - basicAuth: []
    definitions:
      Categories:
        properties:
          categories:
            type: array
            items:
              $ref: '#/definitions/Category'
      Category:
        type: object
        properties:
          name:
            type: string
          subCategories:
            type: array
            items:
              $ref: '#/definitions/Service'
      Service:
        type: object
        properties:
          id:
            type: integer
          name:
            type: string
    responses:
      200:
        description: A list of services
        schema:
          $ref: '#/definitions/Categories'
    """
    services_data = db.session.query(ServiceType, ServiceCategory)\
        .join(ServiceCategory, ServiceType.category_id == ServiceCategory.id)\
        .filter(ServiceCategory.name.in_(['Medical', 'Rehabilitation']))\
        .all()

    services = [s.ServiceType.serializable for s in services_data]

    result = []
    for key, group in groupby(services, key=itemgetter('category')):
        result.append(dict(name=key['name'],
                           subCategories=list(dict(id=s['id'], name=s['name']) for s in group)))

    return jsonify(categories=result), 200


@api.route('/services/<service_type_id>/regions/<region_id>/prices', methods=['GET'], endpoint='filter_services')
@login_required
@role_required('buyer')
@is_service_current_framework
def filter(service_type_id, region_id):
    """Filter suppliers and prices (role=buyer)
    ---
    tags:
      - services
    security:
      - basicAuth: []
    parameters:
      - name: service_type_id
        in: path
        type: integer
        required: true
        default: all
      - name: region_id
        in: path
        type: integer
        required: true
        default: all
    definitions:
      Prices:
        type: object
        properties:
          alert:
            schema:
              $ref: '#/definitions/Alert'
          categories:
            type: array
            items:
              $ref: '#/definitions/SubService'
      SubService:
        type: object
        properties:
          name:
            type: string
          suppliers:
            type: array
            items:
              $ref: '#/definitions/SupplierPrice'
      SupplierPrice:
        type: object
        properties:
          email:
            type: string
          name:
            type: string
          phone:
            type: string
          price:
            type: string
          code:
            type: integer
      Alert:
        type: object
        properties:
          message:
            type: string
          type:
            type: string
    responses:
      200:
        description: A list of prices
        schema:
          $ref: '#/definitions/Prices'
    """
    service_type = db.session.query(ServiceType).get(service_type_id)
    region = db.session.query(Region).get(region_id)

    if service_type is None or region is None:
        return jsonify(), 404

    today = pendulum.today(current_app.config['DEADLINES_TZ_NAME']).date()

    prices = db.session.query(ServiceTypePrice, Supplier, ServiceSubType)\
        .join(Supplier, ServiceTypePrice.supplier_code == Supplier.code)\
        .outerjoin(ServiceSubType, ServiceTypePrice.sub_service_id == ServiceSubType.id)\
        .filter(
            ServiceTypePrice.service_type_id == service_type_id,
            ServiceTypePrice.region_id == region_id,
            ServiceTypePrice.is_current_price(today))\
        .distinct(ServiceSubType.name, ServiceTypePrice.supplier_code, ServiceTypePrice.service_type_id,
                  ServiceTypePrice.sub_service_id, ServiceTypePrice.region_id)\
        .order_by(ServiceSubType.name, ServiceTypePrice.supplier_code.desc(),
                  ServiceTypePrice.service_type_id.desc(), ServiceTypePrice.sub_service_id.desc(),
                  ServiceTypePrice.region_id.desc(), ServiceTypePrice.updated_at.desc())\
        .all()

    supplier_prices = []
    for price, supplier, sub_service in prices:
        supplier_prices.append((
            None if not sub_service else sub_service.name,
            {
                'price': '{:1,.2f}'.format(price.price),
                'name': supplier.name,
                'phone': supplier.data.get('contact_phone', None),
                'email': supplier.data.get('contact_email', None),
                'code': supplier.code
            }
        ))

    result = []
    for key, group in groupby(supplier_prices, key=lambda x: x[0]):
        result.append(dict(name=key, suppliers=list(s[1] for s in group)))

    alert = ALERTS['none'] if len(result) == 0 else ALERTS[service_type.fee_type.lower()]

    return jsonify(alert=alert, categories=result), 200
