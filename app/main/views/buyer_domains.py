from dmapiclient.audit import AuditTypes
from sqlalchemy.exc import IntegrityError
from flask import jsonify, abort

from .. import main
from ... import db
from ...models import BuyerEmailDomain, AuditEvent
from ...validation import validate_buyer_email_domain_json_or_400, buyer_email_already_approved
from ...utils import get_json_from_request, json_has_required_keys, validate_and_return_updater_request


@main.route('/buyer-email-domain', methods=['POST'])
def create_buyer_email_domain():
    updater_json = validate_and_return_updater_request()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["buyerEmailDomains"])
    validate_buyer_email_domain_json_or_400(json_payload["buyerEmailDomains"])

    new_domain = json_payload["buyerEmailDomains"]['domainName'].lower()

    if buyer_email_already_approved(BuyerEmailDomain.query.all(), new_domain):
        abort(409, "Domain name {} has already been approved".format(new_domain))

    buyer_email_domain = BuyerEmailDomain(domain_name=new_domain)
    db.session.add(buyer_email_domain)
    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        abort(400, e.orig)

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

    return jsonify(buyerEmailDomains=buyer_email_domain.serialize()), 201
