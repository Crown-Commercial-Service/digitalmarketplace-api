from flask import jsonify, request, abort
from datetime import datetime

from app.main import main
from app.models import User
from app import db
from sqlalchemy.exc import IntegrityError

from app.main import helpers
from app.validation import validate_user_json_or_400


@main.route('/users/<string:email_address>', methods=['GET'])
def get_user_by_email(email_address):
    user = User.query.filter(
        User.email_address == email_address
    ).first_or_404()
    return jsonify(users=user.serialize())


@main.route('/users', methods=['PUT'])
def create_user():
    now = datetime.now()
    json_payload = get_json_from_request()

    try:
        user = User.query.filter(
            User.email_address == json_payload['email_address']) \
            .all()
        now = datetime.now()
    except Exception as e:
        print e.message
        return

    http_status = 204
    # if user is None:
    http_status = 201
    user = User(
        email_address=json_payload['email_address'],
        name=json_payload['name'],
        password=json_payload['password'],
        created_at=now,
        last_updated_at=now,
        password_changed_at=now
    )

    db.session.add(user)

    try:
        db.session.commit()
        return http_status
    except IntegrityError:
        db.session.rollback()
        abort(400, "Unknown supplier ID provided")


def get_json_from_request():
    payload = helpers.get_json_from_request(request)
    helpers.json_has_required_keys(payload, ['users'])
    update_json = payload['users']
    validate_user_json_or_400(update_json)
    return update_json
