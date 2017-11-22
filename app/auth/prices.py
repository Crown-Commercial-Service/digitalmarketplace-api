from app import db
from app.models import ServiceTypePrice, Region
from flask import jsonify, request
from app.auth.helpers import abort, parse_date
import pendulum
from app.emails.prices import send_price_change_email


def get_prices(code, service_type_id, category_id, date):
    prices = db.session.query(ServiceTypePrice)\
        .join(ServiceTypePrice.region)\
        .filter(ServiceTypePrice.supplier_code == code,
                ServiceTypePrice.service_type_id == service_type_id,
                ServiceTypePrice.sub_service_id == category_id,
                ServiceTypePrice.is_current_price(date))\
        .distinct(Region.state, Region.name, ServiceTypePrice.supplier_code, ServiceTypePrice.service_type_id,
                  ServiceTypePrice.sub_service_id, ServiceTypePrice.region_id)\
        .order_by(Region.state, Region.name, ServiceTypePrice.supplier_code.desc(),
                  ServiceTypePrice.service_type_id.desc(), ServiceTypePrice.sub_service_id.desc(),
                  ServiceTypePrice.region_id.desc(), ServiceTypePrice.updated_at.desc())\
        .all()

    return jsonify(prices=[p.serializable for p in prices]), 200


def update_prices():
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
