from datetime import datetime
from dmapiclient.audit import AuditTypes
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, DataError
from flask import jsonify, abort, request, current_app

from .. import main
from ... import db, encryption
from ...models import User, AuditEvent, Supplier, Framework, SupplierFramework, DraftService
from ...utils import get_json_from_request, json_has_required_keys, \
    json_has_matching_id, pagination_links, get_valid_page_or_1, validate_and_return_updater_request
from ...validation import validate_user_json_or_400, validate_user_auth_json_or_400, is_valid_buyer_email


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
        ).first_or_404()

        return jsonify(
            users=[user.serialize()],
            links={}
        )

    supplier_code = request.args.get('supplier_code')
    if supplier_code is not None:
        try:
            supplier_code = int(supplier_code)
        except ValueError:
            abort(400, "Invalid supplier_code: {}".format(supplier_code))

        supplier = Supplier.query.filter(Supplier.code == supplier_code).all()
        if not supplier:
            abort(404, "supplier_code '{}' not found".format(supplier_code))

        user_query = user_query.filter(User.supplier_code == supplier_code)

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

    print 'get_json_from_request'
    json_payload = get_json_from_request()
    print json_payload
    print 'has_required_keys'
    json_has_required_keys(json_payload, ["users"])
    print 'json_payload'
    json_payload = json_payload["users"]
    print 'validate'
    validate_user_json_or_400(json_payload)

    print 'query'
    user = User.query.filter(
        User.email_address == json_payload['emailAddress'].lower()).first()

    if user:
        abort(409, "User already exists")

    if 'hashpw' in json_payload and not json_payload['hashpw']:
        password = json_payload['password']
    else:
        password = encryption.hashpw(json_payload['password'])

    print 'User'
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

    if "supplierCode" in json_payload:
        user.supplier_code = json_payload['supplierCode']
        audit_data['supplier_code'] = user.supplier_code

    print 'check_supplier_role'
    check_supplier_role(user.role, user.supplier_code)

    try:
        print 'add'
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
        abort(400, "Invalid supplier code")
    except DataError:
        db.session.rollback()
        abort(400, "Invalid user role")

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
        user_update['password'] = 'updated'
    if 'active' in user_update:
        user.active = user_update['active']
    if 'name' in user_update:
        user.name = user_update['name']
    if 'emailAddress' in user_update:
        user.email_address = user_update['emailAddress']
    if 'role' in user_update:
        if user.role == 'supplier' and user_update['role'] != user.role:
            user.supplier_code = None
            user_update.pop('supplierCode', None)
        user.role = user_update['role']
    if 'supplierCode' in user_update:
        user.supplier_code = user_update['supplierCode']
    if 'locked' in user_update and not user_update['locked']:
        user.failed_login_count = 0

    check_supplier_role(user.role, user.supplier_code)

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

    supplier_frameworks_and_suppliers_and_users = db.session.query(
        SupplierFramework, Supplier, User
    ).join(
        Supplier, User, Framework
    ).filter(
        Framework.slug == framework_slug
    ).filter(
        User.active.is_(True)
    ).all()

    submitted_draft_counts_per_supplier = {}
    user_rows = []

    for sf, s, u in supplier_frameworks_and_suppliers_and_users:

        # always get the declaration status
        declaration_status = sf.declaration.get('status') if sf.declaration else 'unstarted'
        application_status = ''
        application_result = ''
        framework_agreement = ''

        # if framework is pending, live, or expired
        if framework.status != 'open':

            # get number of completed draft services per supplier
            # `application_status` is based on a complete declaration and at least one completed draft service
            if sf.supplier_code not in submitted_draft_counts_per_supplier.keys():
                submitted_draft_counts_per_supplier[sf.supplier_code] = db.session.query(
                    func.count()
                ).filter(
                    DraftService.supplier_code == sf.supplier_code,
                    DraftService.framework_id == sf.framework_id,
                    DraftService.status == 'submitted'
                ).scalar()

            submitted_draft_count = submitted_draft_counts_per_supplier[sf.supplier_code]
            application_status = \
                'application' if submitted_draft_count and declaration_status == 'complete' else 'no_application'
            if sf.on_framework is None:
                application_result = 'no result'
            else:
                application_result = 'pass' if sf.on_framework else 'fail'
            framework_agreement = bool(sf.agreement_returned_at)

        user_rows.append({
            'user_email': u.email_address,
            'user_name': u.name,
            'supplier_code': s.supplier_code,
            'declaration_status': declaration_status,
            'application_status': application_status,
            'framework_agreement': framework_agreement,
            'application_result': application_result
        })

    return jsonify(users=[user for user in user_rows])


@main.route("/users/check-buyer-email", methods=["GET"])
def email_has_valid_buyer_domain():
    email_address = request.args.get('email_address')
    if not email_address:
        abort(400, "'email_address' is a required parameter")

    return jsonify(valid=is_valid_buyer_email(email_address))


def check_supplier_role(role, supplier_code):
    if role == 'supplier' and not supplier_code:
        abort(400, "'supplier_code' is required for users with 'supplier' role")
    elif role != 'supplier' and supplier_code:
        abort(400, "'supplier_code' is only valid for users with 'supplier' role, not '{}'".format(role))
