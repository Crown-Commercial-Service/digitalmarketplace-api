from datetime import datetime
from dmutils.audit import AuditTypes
from sqlalchemy.exc import IntegrityError, DataError
from flask import jsonify, abort, request, current_app

from .. import main
from ... import db, encryption
from ...models import User, AuditEvent, Supplier
from ...utils import get_json_from_request, json_has_required_keys, \
    json_has_matching_id, pagination_links, get_valid_page_or_1
from ...validation import validate_user_json_or_400, validate_user_auth_json_or_400


@main.route('/users/auth', methods=['POST'])
def auth_user():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["authUsers"])
    json_payload = json_payload["authUsers"]
    validate_user_auth_json_or_400(json_payload)

    user = User.get_by_email_address(json_payload['emailAddress'].lower())

    if user is None:
        return jsonify(authorization=False), 404
    elif encryption.authenticate_user(json_payload['password'], user) and user.active:
        user.logged_in_at = datetime.utcnow()
        user.failed_login_count = 0
        db.session.add(user)
        db.session.commit()

        return jsonify(users=user.serialize()), 200
    else:
        user.failed_login_count += 1
        db.session.add(user)
        db.session.commit()

        return jsonify(authorization=False), 403


@main.route('/users/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    user = User.query.filter(
        User.id == user_id
    ).first_or_404()
    return jsonify(users=user.serialize())


@main.route('/users', methods=['GET'])
def list_users():
    user_query = User.query.order_by(User.id)
    page = get_valid_page_or_1()

    # email_address is a primary key
    email_address = request.args.get('email_address')
    if email_address:
        user = user_query.filter(
            User.email_address == email_address.lower()
        ).first()

        if not user:
            abort(404, "No user with email_address '{}'".format(email_address))

        return jsonify(
            users=[user.serialize()],
            links={}
        )

    supplier_id = request.args.get('supplier_id')
    if supplier_id is not None:
        try:
            supplier_id = int(supplier_id)
        except ValueError:
            abort(400, "Invalid supplier_id: {}".format(supplier_id))

        supplier = Supplier.query.filter(Supplier.supplier_id == supplier_id).all()
        if not supplier:
            abort(404, "supplier_id '{}' not found".format(supplier_id))

        user_query = user_query.filter(User.supplier_id == supplier_id)

    users = user_query.paginate(
        page=page,
        per_page=current_app.config['DM_API_SERVICES_PAGE_SIZE'],
    )

    return jsonify(
        users=[user.serialize() for user in users.items],
        links=pagination_links(
            users,
            '.list_users',
            request.args
        )
    )


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

    now = datetime.utcnow()
    user = User(
        email_address=json_payload['emailAddress'].lower(),
        name=json_payload['name'],
        role=json_payload['role'],
        password=password,
        active=True,
        created_at=now,
        updated_at=now,
        password_changed_at=now
    )

    audit_data = {}

    if "supplierId" in json_payload:
        user.supplier_id = json_payload['supplierId']
        audit_data['supplier_id'] = user.supplier_id

    check_supplier_role(user.role, user.supplier_id)

    try:
        db.session.add(user)
        db.session.flush()

        audit = AuditEvent(
            audit_type=AuditTypes.create_user,
            user=json_payload['emailAddress'].lower(),
            data=audit_data,
            db_object=user
        )

        db.session.add(audit)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(400, "Invalid supplier id")
    except DataError:
        db.session.rollback()
        abort(400, "Invalid user role")

    return jsonify(users=user.serialize()), 201


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

    if 'password' in user_update:
        user.password = encryption.hashpw(user_update['password'])
        user.password_changed_at = datetime.utcnow()
    if 'active' in user_update:
        user.active = user_update['active']
    if 'name' in user_update:
        user.name = user_update['name']
    if 'role' in user_update:
        user.role = user_update['role']
    if 'supplierId' in user_update:
        user.supplier_id = user_update['supplierId']
    if 'emailAddress' in user_update:
        user.email_address = user_update['emailAddress']
    if 'locked' in user_update and not user_update['locked']:
        user.failed_login_count = 0

    check_supplier_role(user.role, user.supplier_id)

    audit = AuditEvent(
        audit_type=AuditTypes.update_user,
        user=user.email_address,
        data={'update': user_update},
        db_object=user
    )

    db.session.add(user)
    db.session.add(audit)

    try:
        db.session.commit()
        return jsonify(users=user.serialize()), 200
    except (IntegrityError, DataError):
        db.session.rollback()
        abort(400, "Could not update user with: {0}".format(user_update))


def check_supplier_role(role, supplier_id):
    if role == 'supplier' and not supplier_id:
        abort(400, "'supplier_id' is required for users with 'supplier' role")
    elif role != 'supplier' and supplier_id:
        abort(400, "'supplier_id' is only valid for users with 'supplier' role, not '{}'".format(role))
