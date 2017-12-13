from flask import jsonify
from flask_login import current_user, login_required
from app.api import api
from ...models import db, AuditEvent, Brief
from ...utils import (
    get_json_from_request
)
from dmapiclient.audit import AuditTypes


@api.route('/feedback', methods=["POST"])
@login_required
def post_feedback():
    feedback_data = get_json_from_request()

    if feedback_data['object_type'] == 'Brief':
        db_object = Brief.query.filter(
            Brief.id == feedback_data['object_id']
        ).first_or_404()

    feedback = AuditEvent(
        audit_type=AuditTypes.feedback,
        user=current_user.email_address,
        data=feedback_data,
        db_object=db_object
    )

    db.session.add(feedback)
    db.session.commit()

    return jsonify(feedback=feedback), 201
