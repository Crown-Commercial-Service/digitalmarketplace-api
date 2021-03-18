from flask import jsonify, current_app

from dmapiclient.audit import AuditTypes
from dmutils.email.helpers import hash_string

from app import db
from app.callbacks import callbacks
from app.utils import get_json_from_request
from app.models import User, AuditEvent


@callbacks.route('/')
@callbacks.route('')
def callbacks_root():
    return jsonify(status='ok'), 200


@callbacks.route('/notify', methods=['POST'])
def notify_callback():
    notify_data = get_json_from_request()

    email_address = notify_data["to"]
    hashed_email = hash_string(email_address)
    reference = notify_data["reference"]
    status = notify_data["status"]

    # remove PII from response for logging
    # according to docs only "to" has PII
    # https://docs.notifications.service.gov.uk/rest-api.html#delivery-receipts
    clean_notify_data = notify_data.copy()
    del clean_notify_data["to"]

    current_app.logger.info(
        f"Notify callback: {status}: {reference} to {hashed_email}",
        extra=clean_notify_data,
    )

    if status == "permanent-failure":
        user = User.query.filter(
            User.email_address == email_address
        ).first()

        if user and user.active:
            user.active = False
            db.session.add(user)

            audit_event = AuditEvent(
                audit_type=AuditTypes.update_user,
                user='Notify callback',
                data={"user": {"active": False}, "notify_callback_data": notify_data},
                db_object=user,
            )
            db.session.add(audit_event)

            db.session.commit()

            current_app.logger.info(
                f"User account disabled for {hashed_email} after Notify reported permanent delivery "
                "failure."
            )

    elif status.endswith("failure"):
        current_app.logger.warning(
            f"Notify failed to deliver {reference} to {hashed_email}"
        )

    return jsonify(status='ok'), 200
