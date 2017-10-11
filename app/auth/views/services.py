from flask import jsonify
from flask_login import login_required
from collections import defaultdict
from app.auth import auth
from app.utils import get_json_from_request, json_has_required_keys
from app.models import (
    db, Region, ServiceCategory, ServiceType, ServiceTypePrice,
    Supplier, ServiceSubType
)

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
    region_query = db.session.query(Region)
    region_data = defaultdict(list)
    state_region_pairs = []

    for region in region_query.all():
        state_region_list = []
        state_region_list = region.name.split(' ', 1)

        if len(state_region_list) == 1:
            state_region_list.append(None)

        state_region_pairs.append({
            'mainRegion': state_region_list[0],
            'subRegion': {
                'name': state_region_list[1],
                'id': region.id
            }
        })

    state_regions_merged = defaultdict(set)

    for item in state_region_pairs:
        main = item['mainRegion']
        sub = item['subRegion']['name']
        sub_id = item['subRegion']['id']
        state_regions_merged[main].add(tuple(i for i in [sub, sub_id]))

    region_data = [
        {'mainRegion': m, 'subRegions': [{'name': s[0], 'id': s[1]} for s in subs]}
        for m, subs in state_regions_merged.items()
    ]

    return jsonify(regions=region_data), 200


@auth.route('/services', methods=['GET'])
@login_required
def get_category_services():
    services_query = db.session.query(ServiceType, ServiceCategory).\
        join(ServiceCategory, ServiceType.category_id == ServiceCategory.id).\
        filter(ServiceCategory.name.in_(['Medical', 'Rehabilitation']))

    services_data = defaultdict(list)
    main_sub_pairs = []

    for service_type, service_category in services_query.all():
        main_sub_pairs.append({
            'mainCategory': service_category.name,
            'subCategories': {
                'serviceTypeName': service_type.name,
                'serviceTypeId': service_type.id
            }
        })

    sub_category_merged = defaultdict(set)

    for item in main_sub_pairs:
        main = item['mainCategory']
        sub = item['subCategories']['serviceTypeName']
        sub_id = item['subCategories']['serviceTypeId']
        sub_category_merged[main].add(tuple(i for i in [sub, sub_id]))

    services_data = [
        {'mainCategory': m, 'subCategories': [{'serviceTypeName': s[0], 'serviceTypeId': s[1]} for s in subs]}
        for m, subs in sub_category_merged.items()
    ]

    return jsonify(categories=services_data), 200


@auth.route('/seller-catalogue', methods=['POST'])
@login_required
def get_seller_catalogue_data():
    catalogue_json = get_json_from_request()
    json_has_required_keys(catalogue_json, ['serviceTypeId', 'regionId'])

    service_type = db.session.query(ServiceType).get(catalogue_json['serviceTypeId'])

    if service_type is None:
        return jsonify(message='Invalid serviceTypeId'), 500

    price_supplier_query = (
        db.session.query(ServiceTypePrice, Supplier, ServiceSubType)
        .join(Supplier, ServiceTypePrice.supplier_code == Supplier.code)
        .outerjoin(ServiceSubType, ServiceTypePrice.sub_service_id == ServiceSubType.id).filter(
            ServiceTypePrice.service_type_id == catalogue_json['serviceTypeId'],
            ServiceTypePrice.region_id == catalogue_json['regionId']
        )
    )

    price_sup_pairs = []

    for price, supplier, sub_service in price_supplier_query.all():
        price_sup_pairs.append({
            'category': None if not sub_service else sub_service.name,
            'details': {
                'price': price.price,
                'name': supplier.name,
                'phone': supplier.data.get('contact_phone'),
                'email': supplier.data.get('contact_email'),
            }
        })

    sub_category_merged = defaultdict(list)

    for item in price_sup_pairs:
        main = item['category']
        sub = item['details']
        sub_category_merged[main].append(sub)

    price_data = [
        {'category': m, 'suppliers': [s for s in subs]}
        for m, subs in sub_category_merged.items()
    ]

    alert = ALERTS['none'] if len(price_data) == 0 else ALERTS[service_type.fee_type.lower()]

    return jsonify(alert=alert, categories=price_data), 200
