from datetime import datetime

from flask import jsonify, abort

from .. import main
from ... import db, encryption
from ...models import User
from ...utils import get_json_from_request, json_has_required_keys
from ...validation import validate_user_json_or_400, \
    validate_user_auth_json_or_400


@main.route('/users/auth', methods=['POST'])
def auth_user():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["auth_users"])
    json_payload = json_payload["auth_users"]
    validate_user_auth_json_or_400(json_payload)

    user = User.query.filter(
        User.email_address == json_payload['email_address'].lower()).first()

    if user is None:
        return jsonify(authorization=False), 404
    elif encryption.checkpw(json_payload['password'], user.password):
        return jsonify(users=user.serialize()), 200
    else:
        return jsonify(authorization=False), 403


@main.route('/users/<int:user_id>', methods=['GET'])
def get_user_by_email(user_id):
    user = User.query.filter(
        User.id == user_id
    ).first_or_404()
    return jsonify(users=user.serialize())


@main.route('/users', methods=['POST'])
def create_user():

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["users"])
    json_payload = json_payload["users"]
    validate_user_json_or_400(json_payload)

    user = User.query.filter(
        User.email_address == json_payload['email_address'].lower()).first()

    if user:
        abort(409, "User already exists")

    if 'hashpw' in json_payload and not json_payload['hashpw']:
        password = json_payload['password']
    else:
        password = encryption.hashpw(json_payload['password'])

    now = datetime.now()
    user = User(
        email_address=json_payload['email_address'].lower(),
        name=json_payload['name'],
        password=password,
        active=True,
        locked=False,
        created_at=now,
        updated_at=now,
        password_changed_at=now
    )

    db.session.add(user)

    db.session.commit()

    return jsonify(users=user.serialize()), 200
