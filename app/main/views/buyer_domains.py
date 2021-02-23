from dmapiclient.audit import AuditTypes
from sqlalchemy.exc import IntegrityError
from flask import abort, current_app, request, jsonify

from .. import main
from ... import db
from ...models import BuyerEmailDomain, AuditEvent
from ...validation import validate_buyer_email_domain_json_or_400, is_approved_buyer_domain
from ...utils import (
    get_json_from_request,
    get_valid_page_or_1,
    json_has_required_keys,
    paginated_result_response,
    single_result_response,
    validate_and_return_updater_request,
)

RESOURCE_NAME = "buyerEmailDomains"


def get_domain_from_request():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["buyerEmailDomains"])
    validate_buyer_email_domain_json_or_400(json_payload["buyerEmailDomains"])

    return json_payload["buyerEmailDomains"]['domainName'].lower()


@main.route('/buyer-email-domains', methods=['POST'])
def create_buyer_email_domain():
    updater_json = validate_and_return_updater_request()
    new_domain = get_domain_from_request()

    if is_approved_buyer_domain(BuyerEmailDomain.query.all(), new_domain):
        abort(409, "Domain name {} has already been approved".format(new_domain))

    buyer_email_domain = BuyerEmailDomain(domain_name=new_domain)
    db.session.add(buyer_email_domain)
    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    audit = AuditEvent(
        audit_type=AuditTypes.create_buyer_email_domain,
        user=updater_json['updated_by'],
        data={
            'buyerEmailDomainId': buyer_email_domain.id,
            'buyerEmailDomainJson': {'domainName': new_domain}
        },
        db_object=buyer_email_domain,
    )

    db.session.add(audit)
    db.session.commit()

    return single_result_response(RESOURCE_NAME, buyer_email_domain), 201


@main.route('/buyer-email-domains', methods=['DELETE'])
def delete_buyer_email_domain():
    updater_json = validate_and_return_updater_request()

    buyer_email_domain = BuyerEmailDomain.query.filter(
        BuyerEmailDomain.domain_name == get_domain_from_request()
    ).first_or_404()

    audit = AuditEvent(
        audit_type=AuditTypes.delete_buyer_email_domain,
        user=updater_json['updated_by'],
        data={
            'buyerEmailDomainId': buyer_email_domain.id,
            'buyerEmailDomainJson': {'domainName': buyer_email_domain.domain_name}
        },
        db_object=None
    )

    db.session.delete(buyer_email_domain)
    db.session.add(audit)
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, format(e))

    return jsonify(message="done"), 200


@main.route('/buyer-email-domains', methods=['GET'])
def list_buyer_email_domains():
    page = get_valid_page_or_1()

    buyer_email_domains = BuyerEmailDomain.query.order_by(BuyerEmailDomain.domain_name)
    return paginated_result_response(
        result_name=RESOURCE_NAME,
        results_query=buyer_email_domains,
        page=page,
        per_page=current_app.config['DM_API_BUYER_DOMAINS_PAGE_SIZE'],
        endpoint='.list_buyer_email_domains',
        request_args=request.args
    ), 200
