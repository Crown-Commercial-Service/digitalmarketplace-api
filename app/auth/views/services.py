from flask import jsonify
from flask_login import login_required
from app.auth import auth
from app.models import (
    db, Region, ServiceCategory, ServiceType, ServiceTypePrice,
    Supplier, ServiceSubType
)
from itertools import groupby
from operator import itemgetter
from app.auth.helpers import role_required

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
@role_required('supplier')
def get_regions():
    regions_data = db.session.query(Region).order_by(Region.state).all()
    regions = [_.serializable for _ in regions_data]

    result = []
    for key, group in groupby(regions, key=itemgetter('state')):
        result.append(dict(name=key, subRegions=list(dict(id=s['id'], name=s['name']) for s in group)))

    return jsonify(regions=result), 200


@auth.route('/services', methods=['GET'])
@login_required
@role_required('supplier')
def get_category_services():
    services_data = db.session.query(ServiceType, ServiceCategory)\
        .join(ServiceCategory, ServiceType.category_id == ServiceCategory.id)\
        .filter(ServiceCategory.name.in_(['Medical', 'Rehabilitation']))\
        .all()

    services = [s[0].serializable for s in services_data]

    result = []
    for key, group in groupby(services, key=itemgetter('category')):
        result.append(dict(name=key['name'],
                           subCategories=list(dict(id=s['id'], name=s['name']) for s in group)))

    return jsonify(categories=result), 200


@auth.route('/services/<service_type_id>/regions/<region_id>/prices', methods=['GET'])
@login_required
@role_required('supplier')
def get_seller_catalogue_data(service_type_id, region_id):
    service_type = db.session.query(ServiceType).get(service_type_id)
    region = db.session.query(Region).get(region_id)

    if service_type is None or region is None:
        return jsonify(alert=ALERTS['none'], categories=[]), 200

    prices = db.session.query(ServiceTypePrice, Supplier, ServiceSubType)\
        .join(Supplier, ServiceTypePrice.supplier_code == Supplier.code)\
        .outerjoin(ServiceSubType, ServiceTypePrice.sub_service_id == ServiceSubType.id)\
        .filter(
            ServiceTypePrice.service_type_id == service_type_id,
            ServiceTypePrice.region_id == region_id)\
        .order_by(ServiceSubType.name)\
        .all()

    supplier_prices = []
    for price, supplier, sub_service in prices:
        supplier_prices.append((
            None if not sub_service else sub_service.name,
            {
                'price': '{:1,.2f}'.format(price.price),
                'name': supplier.name,
                'phone': supplier.data.get('contact_phone'),
                'email': supplier.data.get('contact_email')
            }
        ))

    result = []
    for key, group in groupby(supplier_prices, key=lambda x: x[0]):
        result.append(dict(name=key, suppliers=list(s[1] for s in group)))

    alert = ALERTS['none'] if len(result) == 0 else ALERTS[service_type.fee_type.lower()]

    return jsonify(alert=alert, categories=result), 200
