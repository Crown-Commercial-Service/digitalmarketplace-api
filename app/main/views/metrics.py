from .. import main
from . import briefs, users, suppliers
from ...models import Brief, User, Supplier, BriefResponse
from ... import db
from sqlalchemy import desc, func, select
import pendulum
import json
from flask import jsonify


@main.route('/metrics', methods=['GET'])
def get_metrics():
    timestamp = pendulum.now().to_iso8601_string()
    metrics = {}
    brief_metrics = json.loads(briefs.get_briefs_stats().data)["briefs"]
    for key, metric in brief_metrics.items():
        if type(metric) == int:
            metrics["briefs_"+key] = {"value": metric, "ts": timestamp}

    brief_response_count = BriefResponse.query\
        .filter(BriefResponse.data.isnot(None))\
        .order_by(desc(BriefResponse.created_at)).all().count(BriefResponse.id)
    metrics["brief_response_count"] = {"value": brief_response_count, "ts": timestamp}

    buyer_count = json.loads(users.get_buyers_stats().data)["buyers"]['total']
    metrics["buyer_count"] = {"value": buyer_count, "ts": timestamp}
    supplier_count = json.loads(suppliers.get_suppliers_stats().data)["suppliers"]['total']
    metrics["supplier_count"] = {"value": supplier_count, "ts": timestamp}
    return jsonify(metrics)


@main.route('/metrics/history', methods=['GET'])
def get_historical_metrics():
    metrics = {}

    metrics["briefs_total_count"] = []
    brief_day = func.date_trunc('day', Brief.published_at)
    briefs_by_day = select([brief_day, func.count(brief_day)])\
        .where(Brief.withdrawn_at.is_(None))\
        .where(Brief.published_at.isnot(None))\
        .order_by(brief_day)\
        .group_by(brief_day)
    for (day, count) in db.session.execute(briefs_by_day):
        print metrics["briefs_total_count"].append({"value": count, "ts": pendulum.instance(day).to_iso8601_string()})

    metrics["brief_response_count"] = []
    brief_responses_day = func.date_trunc('day', BriefResponse.created_at)
    brief_responses_by_day = select([brief_responses_day, func.count(brief_responses_day)]) \
        .order_by(brief_responses_day) \
        .group_by(brief_responses_day)
    for (day, count) in db.session.execute(brief_responses_by_day):
        print metrics["brief_response_count"].append({"value": count, "ts": pendulum.instance(day).to_iso8601_string()})

    metrics["buyer_count"] = []
    buyer_day = func.date_trunc('day', User.created_at)
    buyers_by_day = select([buyer_day, func.count(buyer_day)])\
        .where(User.email_address.contains("+").is_(False) | User.email_address.contains("digital.gov.au").is_(False))\
        .where(User.active.is_(True)) \
        .where(User.role == 'buyer') \
        .order_by(buyer_day)\
        .group_by(buyer_day)
    for (day, count) in db.session.execute(buyers_by_day):
        print metrics["buyer_count"].append({"value": count, "ts": pendulum.instance(day).to_iso8601_string()})

    metrics["supplier_count"] = []
    supplier_day = func.date_trunc('day', Supplier.creation_time)
    suppliers_by_day = select([supplier_day, func.count(supplier_day)]) \
        .where(Supplier.abn != Supplier.DUMMY_ABN) \
        .order_by(supplier_day) \
        .group_by(supplier_day)
    for (day, count) in db.session.execute(suppliers_by_day):
        print metrics["supplier_count"].append({"value": count, "ts": pendulum.instance(day).to_iso8601_string()})

    return jsonify(metrics)
