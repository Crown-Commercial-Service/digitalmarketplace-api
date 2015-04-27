from datetime import datetime
from sqlalchemy.exc import IntegrityError
from flask import jsonify, abort, request

from .. import main
from ... import db, encryption
from ...models import User
from ...utils import get_json_from_request, json_has_required_keys, \
    json_has_matching_id
from ...validation import validate_user_json_or_400, \
    validate_user_auth_json_or_400


@main.route('/users/auth', methods=['POST'])
def auth_user():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["authUsers"])
    json_payload = json_payload["authUsers"]
    validate_user_auth_json_or_400(json_payload)

    user = User.query.filter(
        User.email_address == json_payload['emailAddress'].lower()).first()

    if user is None:
        return jsonify(authorization=False), 404
    elif encryption.checkpw(json_payload['password'], user.password):
        return jsonify(users=user.serialize()), 200
    else:
        return jsonify(authorization=False), 403


@main.route('/users/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    user = User.query.filter(
        User.id == user_id
    ).first_or_404()
    return jsonify(users=user.serialize())


@main.route('/users', methods=['GET'])
def get_user_by_email():
    email_address = request.args.get('email')
    user = User.query.filter(
        User.email_address == email_address.lower()
    ).first_or_404()
    return jsonify(users=user.serialize())


@main.route('/users', methods=['POST'])
def create_user():

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["users"])
    json_payload = json_payload["users"]
    validate_user_json_or_400(json_payload)

    user = User.query.filter(
        User.email_address == json_payload['emailAddress'].lower()).first()

    if user:
        abort(409, "User already exists")

    if 'hashpw' in json_payload and not json_payload['hashpw']:
        password = json_payload['password']
    else:
        password = encryption.hashpw(json_payload['password'])

    now = datetime.now()
    user = User(
        email_address=json_payload['emailAddress'].lower(),
        name=json_payload['name'],
        role=json_payload['role'],
        password=password,
        active=True,
        locked=False,
        created_at=now,
        updated_at=now,
        password_changed_at=now
    )

    if "supplierId" in json_payload:
        user.supplier_id = json_payload['supplierId']

    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(400, "Invalid supplier id")

    return jsonify(users=user.serialize()), 200


@main.route('/users/<int:user_id>', methods=['POST'])
def update_user(user_id):
    """
        Update a user. Looks user up in DB, and updates where necessary.
    """

    user = User.query.filter(
        User.id == user_id
    ).first_or_404()

    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["users"])
    user_update = json_payload["users"]

    json_has_matching_id(user_update, user_id)

    now = datetime.now()
    user.updated_at = now
    if 'password' in user_update:
        user.password = encryption.hashpw(user_update['password'])
        user.password_changed_at = now
    if 'active' in user_update:
        user.active = user_update['active']
    if 'locked' in user_update:
        user.locked = user_update['locked']
    if 'name' in user_update:
        user.name = user_update['name']
    if 'role' in user_update:
        user.role = user_update['role']
    if 'supplierId' in user_update:
        user.supplier_id = user_update['supplierId']
    if 'emailAddress' in user_update:
        user.email_address = user_update['emailAddress']

    db.session.add(user)

    try:
        db.session.commit()
        return jsonify(message="done"), 200
    except IntegrityError as e:
        db.session.rollback()
        abort(400, "Could not update user with: {0}".format(user_update))
