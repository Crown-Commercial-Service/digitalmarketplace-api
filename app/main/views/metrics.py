from .. import main
from . import briefs, users, suppliers
from ...models import Application, Brief, Domain, User, Supplier, SupplierDomain, BriefResponse
from ... import db
from sqlalchemy import desc, func, select, and_
import pendulum
import json
import io
import csv
from collections import defaultdict
from flask import jsonify, make_response
from app.api.services import key_values_service


@main.route('/metrics', methods=['GET'])
def get_metrics():
    key_values = key_values_service.get_by_keys(
        'brief_metrics',
        'brief_response_metrics',
        'total_contracted',
        'supplier_metrics',
        'awarded_to_smes'
    )
    metrics = {}
    for kv in key_values:
        updated_at = kv['updated_at'].to_iso8601_string()
        if kv['key'] == 'brief_metrics':
            for k, v in kv['data'].iteritems():
                metrics["briefs_" + k] = {"value": v, "ts": updated_at}
        elif kv['key'] == 'total_contracted':
            metrics['total_contracted'] = {"value": kv['data']['total'], "ts": updated_at}
        elif kv['key'] == 'awarded_to_smes':
            metrics['awarded_to_smes'] = {"value": kv['data']['total'], "ts": updated_at}
        elif kv['key'] == 'brief_response_metrics':
            metrics['brief_response_count'] = {"value": kv['data']['total'], "ts": updated_at}
        elif kv['key'] == 'supplier_metrics':
            metrics['supplier_count'] = {"value": kv['data']['total'], "ts": updated_at}

    return jsonify(metrics)


@main.route('/metrics/domains', methods=['GET'])
def get_domain_metrics():
    metrics = {}

    query = '''
                            SELECT name, count(status), status::TEXT
                            FROM
                              supplier_domain INNER JOIN domain ON supplier_domain.domain_id = domain.id
                              WHERE status = 'assessed' OR status = 'unassessed'
                            GROUP BY name, status::TEXT
                            UNION
                            SELECT key, count(*),
                            (CASE
                                WHEN application.status = 'submitted' THEN 'submitted'
                                WHEN application.status = 'saved' THEN 'unsubmitted'
                            END) status
                            FROM
                              application, json_each(application.data->'services') badge
                            WHERE "value"::TEXT = 'true'
                            AND (application.status = 'saved' OR application.status = 'submitted')
                            AND (application.type = 'new' OR application.type = 'upgrade')
                            GROUP BY key, status
                            '''
    for (domain, count, status) in db.session.execute(query).fetchall():
        if domain not in metrics:
            metrics[domain] = {}
            metrics[domain]['domain'] = domain
            metrics[domain]['timestamp'] = pendulum.now().to_iso8601_string()
        metrics[domain][status] = count

    metrics = list(metrics.values())
    return jsonify(metrics)


@main.route('/metrics/applications/seller_types', methods=['GET'])
def get_seller_type_metrics():
    metrics = {}

    query = "SELECT key, count(*) FROM application, json_each(application.data->'seller_type') badge " \
            "where key != 'recruiter' " \
            "AND (application.type = 'new' OR application.type = 'upgrade') GROUP BY key " \
            "union select 'recruiter', count(*) from application where application.data->>'recruiter' = 'yes' " \
            "AND (application.type = 'new' OR application.type = 'upgrade')" \
            "UNION select 'product', count(*) FROM application WHERE application.data->'products'->'0' IS NOT null " \
            "AND (application.type = 'new' OR application.type = 'upgrade')"
    for (seller_type, count) in db.session.execute(query).fetchall():
        metrics[seller_type] = {}
        metrics[seller_type]['seller_type'] = seller_type
        metrics[seller_type]['timestamp'] = pendulum.now().to_iso8601_string()
        metrics[seller_type]['count'] = count

    metrics = list(metrics.values())
    return jsonify(metrics)


@main.route('/metrics/applications/steps', methods=['GET'])
def get_step_metrics():
    metrics = {}

    query = "SELECT key, count(*) FROM application, json_each(application.data->'steps') steps WHERE " \
            "(application.status = 'saved' OR application.status = 'submitted')" \
            "AND (application.type = 'new' OR application.type = 'upgrade')GROUP BY key"
    for (step, count) in db.session.execute(query).fetchall():
        metrics[step] = {}
        metrics[step]['step'] = step
        metrics[step]['timestamp'] = pendulum.now().to_iso8601_string()
        metrics[step]['count'] = count

    metrics = list(metrics.values())
    return jsonify(metrics)


@main.route('/metrics/applications', methods=['GET'])
def get_application_metrics():
    timestamp = pendulum.now().to_iso8601_string()
    metrics = {}

    application_count = Application.query.count()
    metrics["application_total_count"] = {"value": application_count, "ts": timestamp}
    application_existing_seller_count = Application.query\
        .filter(Application.supplier_code.isnot(None)).count()
    metrics["application_new_seller_count"] = {"value": application_count - application_existing_seller_count,
                                               "ts": timestamp}
    metrics["application_existing_seller_count"] = {"value": application_existing_seller_count, "ts": timestamp}

    suppliers_total = Supplier.query.filter(Supplier.abn != Supplier.DUMMY_ABN).count()
    suppliers_with_apps_count = Supplier.query.filter(Supplier.abn != Supplier.DUMMY_ABN)\
        .join(Application, and_(Application.supplier_code == Supplier.code)).distinct(Supplier.id).count()
    metrics["suppliers_with_application_count"] = \
        {"value": suppliers_with_apps_count, "ts": timestamp}
    metrics["suppliers_without_application_count"] = \
        {"value": suppliers_total - suppliers_with_apps_count, "ts": timestamp}

    applications_by_status = select([Application.status,
                                     func.count(Application.status), func.count(Application.supplier_code)]) \
        .order_by(Application.status) \
        .group_by(Application.status)
    for (status, count, existing_seller) in db.session.execute(applications_by_status):
        metrics["application_status_{}_total_count".format(status)] = \
            {"value": count, "ts": timestamp}
        metrics["application_status_{}_existing_seller_count".format(status)] = \
            {"value": existing_seller, "ts": timestamp}
        metrics["application_status_{}_new_seller_count".format(status)] = \
            {"value": count - existing_seller, "ts": timestamp}

    for status in ['saved', 'submitted', 'approved', 'approval_rejected', 'complete', 'assessment_rejected']:
        for category in ['existing_seller', 'new_seller', 'total']:
            if "application_status_{}_{}_count".format(status, category) not in metrics:
                metrics["application_status_{}_{}_count".format(status, category)] = {"value": 0, "ts": timestamp}

    return jsonify(metrics)


@main.route('/metrics/applications/history', methods=['GET'])
def get_application_historical_metrics():
    metrics = defaultdict(list)
    period = pendulum.period(pendulum.Pendulum(2016, 11, 1), pendulum.tomorrow())
    for dt in period.range('days'):
        date = dt.to_date_string()
        timestamp = dt.to_iso8601_string()
        query = '''
  WITH app_metrics AS (SELECT type, count(*) total_count
                FROM
                  (SELECT DISTINCT ON (object_id) date_trunc('day', created_at) AS day, type, object_id FROM audit_event
                  WHERE ((object_type = 'Application'
                          AND object_id NOT IN (SELECT id FROM application WHERE status = 'deleted') )
                          OR object_type = 'SupplierDomain')
                  AND created_at < :date
                  ORDER BY object_id, created_at DESC ) a
                GROUP BY type)
    SELECT * FROM app_metrics
    UNION SELECT 'started_application', sum(total_count) FROM app_metrics
      WHERE type IN ('submit_application','approve_application','create_application','revert_application')
    UNION SELECT 'completed_application', sum(total_count) FROM app_metrics
      WHERE type IN ('submit_application','approve_application','revert_application')
                '''
        for row in db.session.execute(query, {'date': date}).fetchall():
            metrics[row['type'] + "_count"].append({"value": row["total_count"], "ts": timestamp})

    return jsonify(metrics)


@main.route('/metrics/applications.csv', methods=['GET'])
def get_application_metrics_csv():
    metrics = json.loads(get_application_metrics().data)
    timestamp = pendulum.now().to_iso8601_string()
    si = io.StringIO()

    writer = csv.writer(si, delimiter=',', quotechar='"')
    writer.writerow(metrics.keys())
    writer.writerow([timestamp] + [x['value'] for x in metrics.values()])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=application_metrics.csv"
    output.headers["Content-type"] = "text/csv"
    return output


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
        metrics["briefs_total_count"].append({"value": count, "ts": pendulum.instance(day).to_iso8601_string()})

    metrics["brief_response_count"] = []
    brief_responses_day = func.date_trunc('day', BriefResponse.created_at)
    brief_responses_by_day = select([brief_responses_day, func.count(brief_responses_day)]) \
        .order_by(brief_responses_day) \
        .group_by(brief_responses_day)
    for (day, count) in db.session.execute(brief_responses_by_day):
        metrics["brief_response_count"].append({"value": count, "ts": pendulum.instance(day).to_iso8601_string()})

    metrics["buyer_count"] = []
    buyer_day = func.date_trunc('day', User.created_at)
    buyers_by_day = select([buyer_day, func.count(buyer_day)])\
        .where(User.email_address.contains("+").is_(False) | User.email_address.contains("digital.gov.au").is_(False))\
        .where(User.active.is_(True)) \
        .where(User.role == 'buyer') \
        .order_by(buyer_day)\
        .group_by(buyer_day)
    for (day, count) in db.session.execute(buyers_by_day):
        metrics["buyer_count"].append({"value": count, "ts": pendulum.instance(day).to_iso8601_string()})

    metrics["supplier_count"] = []
    supplier_day = func.date_trunc('day', Supplier.creation_time)
    suppliers_by_day = select([supplier_day, func.count(supplier_day)]) \
        .where(Supplier.abn != Supplier.DUMMY_ABN) \
        .order_by(supplier_day) \
        .group_by(supplier_day)
    for (day, count) in db.session.execute(suppliers_by_day):
        metrics["supplier_count"].append({"value": count, "ts": pendulum.instance(day).to_iso8601_string()})

    return jsonify(metrics)
