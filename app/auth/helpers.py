from app import db
from flask import current_app
from dmapiclient.audit import AuditTypes
from app.emails.users import send_existing_seller_notification, send_existing_application_notification
from app.utils import get_json_from_request, json_has_required_keys
from app.models import AuditEvent


def get_duplicate_users(email_address=None):
    duplicate = {"duplicate": None}
    if email_address is not None:
        email_address = email_address
    else:
        json_payload = get_json_from_request()
        json_has_required_keys(json_payload, ["email_address"])
        email_address = json_payload["email_address"]

    domain = email_address.split('@')[-1]

    if domain in current_app.config['GENERIC_EMAIL_DOMAINS']:
        return duplicate

    supplier_code = db.session.execute("""
        select distinct(supplier_code) from vuser
        where email_domain = :domain
    """, {'domain': domain}).fetchone()

    if (supplier_code and supplier_code[0]):
        send_existing_seller_notification(email_address, supplier_code[0])
        duplicate_audit_event(email_address, {'supplier_code': supplier_code[0]})
        duplicate['duplicate'] = {"supplier_code": supplier_code[0]}
        return duplicate

    application_id = db.session.execute("""
        select distinct(application_id) from vuser
        where email_domain = :domain
    """, {'domain': domain}).fetchone()

    if (application_id and application_id[0]):
        send_existing_application_notification(email_address, application_id[0])
        duplicate_audit_event(email_address, {'application_id': application_id[0]})
        duplicate['duplicate'] = {"application_id": application_id[0]}
        return duplicate

    else:
        return duplicate


def duplicate_audit_event(email_address, data):
    audit = AuditEvent(
        audit_type=AuditTypes.duplicate_supplier,
        user=email_address,
        data=data,
        db_object=None
    )

    db.session.add(audit)
    db.session.commit()
