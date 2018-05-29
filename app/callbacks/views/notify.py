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

    if notify_data['status'] == 'permanent-failure':
        user = User.query.filter(
            User.email_address == notify_data['to']
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
                "User account disabled for {hashed_email} after Notify reported permanent delivery "
                "failure.".format(hashed_email=hash_string(notify_data['to']))
            )

    elif notify_data['status'] == 'technical-failure':
        current_app.logger.warning("Notify failed to deliver {reference} to {hashed_email}".format(
            reference=notify_data['reference'],
            hashed_email=hash_string(notify_data['to']),
        ))

    return jsonify(status='ok'), 200
