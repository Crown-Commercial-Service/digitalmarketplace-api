from datetime import datetime
from dmapiclient.audit import AuditTypes
from sqlalchemy.orm import lazyload
from sqlalchemy.exc import IntegrityError, DataError
from flask import jsonify, abort, request, current_app

from .. import main
from ... import db, encryption
from ...models import User, AuditEvent, Supplier, Framework, SupplierFramework, BuyerEmailDomain
from ...utils import get_json_from_request, json_has_required_keys, \
    json_has_matching_id, pagination_links, get_valid_page_or_1, validate_and_return_updater_request
from ...validation import validate_user_json_or_400, validate_user_auth_json_or_400, \
    buyer_email_address_has_approved_domain


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
        single_user = user_query.filter(
            User.email_address == email_address.lower()
        ).first_or_404()

        return jsonify(
            users=[single_user.serialize()],
            links={}
        )

    role = request.args.get('role')
    if role:
        if role in User.ROLES:
            user_query = user_query.filter(
                User.role == role
            )
        else:
            abort(400, 'Invalid user role: {}'.format(role))

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
        links=pagination_links(users, '.list_users', request.args)
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
        phone_number=json_payload.get('phoneNumber') or None,
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
    except DataError as e:
        db.session.rollback()
        abort(400, "Data Error: {}".format(e))

    return jsonify(users=user.serialize()), 201


@main.route('/users/<int:user_id>', methods=['POST'])
def update_user(user_id):
    """
        Update a user. Looks user up in DB, and updates where necessary.
    """
    update_details = validate_and_return_updater_request()

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
        user.failed_login_count = 0
        user_update['password'] = 'updated'
    if 'active' in user_update:
        user.active = user_update['active']
    if 'name' in user_update:
        user.name = user_update['name']
    if 'emailAddress' in user_update:
        user.email_address = user_update['emailAddress']
    if 'role' in user_update:
        if user.role == 'supplier' and user_update['role'] != user.role:
            user.supplier_id = None
            user_update.pop('supplierId', None)
        user.role = user_update['role']
    if 'supplierId' in user_update:
        user.supplier_id = user_update['supplierId']
    if 'locked' in user_update and not user_update['locked']:
        user.failed_login_count = 0

    check_supplier_role(user.role, user.supplier_id)

    audit = AuditEvent(
        audit_type=AuditTypes.update_user,
        user=update_details.get('updated_by', 'no user data'),
        data={
            'user': user.email_address,
            'update': user_update
        },
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


@main.route('/users/export/<framework_slug>', methods=['GET'])
def export_users_for_framework(framework_slug):

    # 400 if framework slug is invalid
    framework = Framework.query.filter(Framework.slug == framework_slug).first()
    if not framework:
        abort(400, 'invalid framework')

    if framework.status == 'coming':
        abort(400, 'framework not yet open')

    suppliers_with_a_complete_service = frozenset(framework.get_supplier_ids_for_completed_service())
    supplier_frameworks_and_users = db.session.query(
        SupplierFramework, User
    ).filter(
        SupplierFramework.supplier_id == User.supplier_id
    ).filter(
        SupplierFramework.framework_id == framework.id
    ).filter(
        User.active.is_(True)
    ).options(
        lazyload(User.supplier),
        lazyload(SupplierFramework.supplier),
        lazyload(SupplierFramework.framework),
        lazyload(SupplierFramework.prefill_declaration_from_framework),
        lazyload(SupplierFramework.framework_agreements),
    ).order_by(
        SupplierFramework.supplier_id,
        User.id,
    ).all()

    user_rows = []

    for sf, u in supplier_frameworks_and_users:

        # always get the declaration status
        declaration_status = sf.declaration.get('status') if sf.declaration else 'unstarted'
        application_status = 'application' if (
            declaration_status == 'complete' and sf.supplier_id in suppliers_with_a_complete_service
        ) else 'no_application'
        application_result = ''
        framework_agreement = ''
        variations_agreed = ''

        # if framework is pending, live, or expired
        if framework.status != 'open':
            if sf.on_framework is None:
                application_result = 'no result'
            else:
                application_result = 'pass' if sf.on_framework else 'fail'
            framework_agreement = bool(getattr(sf.current_framework_agreement, 'signed_agreement_returned_at', None))
            variations_agreed = ', '.join(sf.agreed_variations.keys()) if sf.agreed_variations else ''

        user_rows.append({
            'email address': u.email_address,
            'user_name': u.name,
            'supplier_id': sf.supplier_id,
            'declaration_status': declaration_status,
            'application_status': application_status,
            'framework_agreement': framework_agreement,
            'application_result': application_result,
            'variations_agreed': variations_agreed
        })

    return jsonify(users=[user for user in user_rows])


@main.route("/users/check-buyer-email", methods=["GET"])
def email_has_valid_buyer_domain():
    email_address = request.args.get('email_address')
    if not email_address:
        abort(400, "'email_address' is a required parameter")

    domain_ok = buyer_email_address_has_approved_domain(BuyerEmailDomain.query.all(), email_address)
    return jsonify(valid=domain_ok)


def check_supplier_role(role, supplier_id):
    if role == 'supplier' and not supplier_id:
        abort(400, "'supplierId' is required for users with 'supplier' role")
    elif role != 'supplier' and supplier_id:
        abort(400, "'supplierId' is only valid for users with 'supplier' role, not '{}'".format(role))
