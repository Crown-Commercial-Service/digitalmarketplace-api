from flask import jsonify
from flask_login import current_user, login_required
from app.auth import auth
from ...models import db, AuditEvent, Brief
from ...utils import (
    get_json_from_request
)


@login_required
@auth.route('/feedback', methods=["POST"])
def post_feedback():
    feedback_data = get_json_from_request()

    feedback = AuditEvent(
        audit_type='feedback',
        user=current_user.email_address,
        data=feedback_data,
        db_object=Brief.query.filter(
            Brief.id == feedback_data['object_id']
        ).first_or_404()
    )

    db.session.add(feedback)
    db.session.commit()

    return jsonify(feedback=feedback), 201
