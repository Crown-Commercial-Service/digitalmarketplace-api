from flask import jsonify
from flask_login import login_required
from app.auth import auth
from app.utils import get_json_from_request, json_has_required_keys
from app.models import (
    db, Region, ServiceCategory, ServiceType, ServiceTypePrice,
    Supplier, ServiceSubType
)
from itertools import groupby
from operator import itemgetter

ALERTS = {
    'fixed': {
        'type': 'info',
        'message': 'This service is a fixed fee - inclusive of travel, assessment and report'
    },
    'hourly': {
        'type': 'warning',
        'message': 'The prices for this service are per hour. Travel can be charged.'
    },
    'none': {
        'type': 'warning',
        'message': 'There are no services provided for that region.'
    }
}


@auth.route('/regions', methods=['GET'])
@login_required
def get_regions():
    regions_data = db.session.query(Region).order_by(Region.state).all()
    regions = [_.serializable for _ in regions_data]

    result = []
    for key, group in groupby(regions, key=itemgetter('state')):
        result.append(dict(mainRegion=key, subRegions=list(dict(id=s['id'], name=s['name']) for s in group)))

    return jsonify(regions=result), 200


@auth.route('/services', methods=['GET'])
@login_required
def get_category_services():
    services_data = db.session.query(ServiceType, ServiceCategory)\
        .join(ServiceCategory, ServiceType.category_id == ServiceCategory.id)\
        .filter(ServiceCategory.name.in_(['Medical', 'Rehabilitation']))\
        .all()

    services = [s[0].serializable for s in services_data]

    result = []
    for key, group in groupby(services, key=itemgetter('category')):
        result.append(dict(mainCategory=key['name'],
                           subCategories=list(dict(serviceTypeId=s['id'], serviceTypeName=s['name']) for s in group)))

    return jsonify(categories=result), 200


@auth.route('/seller-catalogue', methods=['POST'])
@login_required
def get_seller_catalogue_data():
    catalogue_json = get_json_from_request()
    json_has_required_keys(catalogue_json, ['serviceTypeId', 'regionId'])

    service_type = db.session.query(ServiceType).get(catalogue_json['serviceTypeId'])
    region = db.session.query(Region).get(catalogue_json['regionId'])

    if service_type is None or region is None:
        return jsonify(alert=ALERTS['none'], categories=[]), 200

    prices = db.session.query(ServiceTypePrice, Supplier, ServiceSubType)\
        .join(Supplier, ServiceTypePrice.supplier_code == Supplier.code)\
        .outerjoin(ServiceSubType, ServiceTypePrice.sub_service_id == ServiceSubType.id)\
        .filter(
            ServiceTypePrice.service_type_id == catalogue_json['serviceTypeId'],
            ServiceTypePrice.region_id == catalogue_json['regionId'])\
        .order_by(ServiceSubType.name)\
        .all()

    supplier_prices = []
    for price, supplier, sub_service in prices:
        supplier_prices.append((
            None if not sub_service else sub_service.name,
            {
                'price': price.price,
                'name': supplier.name,
                'phone': supplier.data.get('contact_phone'),
                'email': supplier.data.get('contact_email')
            }
        ))

    result = []
    for key, group in groupby(supplier_prices, key=lambda x: x[0]):
        result.append(dict(category=key, suppliers=list(s[1] for s in group)))

    alert = ALERTS['none'] if len(result) == 0 else ALERTS[service_type.fee_type.lower()]

    return jsonify(alert=alert, categories=result), 200
