from datetime import datetime

from dmapiclient.audit import AuditTypes
from sqlalchemy import func
from sqlalchemy.orm import lazyload
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.sql.expression import false as sql_false, and_ as sql_and
from flask import abort, current_app, jsonify, request

from dmutils.config import convert_to_boolean
from dmutils.email.helpers import hash_string

from .. import main
from ... import db, encryption
from ...models import AuditEvent, BuyerEmailDomain, Framework, Service, Supplier, SupplierFramework, User
from ...supplier_utils import (
    check_supplier_role,
    company_details_confirmed_if_required_for_framework,
)
from ...utils import (
    get_json_from_request,
    get_valid_page_or_1,
    json_has_required_keys,
    json_has_matching_id,
    paginated_result_response,
    single_result_response,
    validate_and_return_updater_request,
)
from ...validation import (
    admin_email_address_has_approved_domain,
    buyer_email_address_has_approved_domain,
    buyer_email_address_first_approved_domain,
    is_valid_email_address,
    validate_user_auth_json_or_400,
    validate_user_json_or_400,
)

RESOURCE_NAME = "users"


@main.route('/users/auth', methods=['POST'])
def auth_user():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ["authUsers"])
    json_payload = json_payload["authUsers"]
    validate_user_auth_json_or_400(json_payload)

    user = User.query.filter(
        User.email_address == json_payload['emailAddress'].lower()
    ).options(
        # specifying a lazyload here to satisfy the FOR UPDATE OF's limitations, but inevitably the supplier
        # will be fetched on-demand when the result comes to be serialized.
        # the FOR UPDATE lock is required to prevent a race condition when incrementing user.failed_login_count
        lazyload(User.supplier),
    ).with_for_update(of=User).first()

    if user is None:
        # 'Authenticate' an inactive, unlocked user and ignore the result, to mitigate against timing attacks.
        # The extra DB query provides us with roughly the correct timing, which avoids us having to serialize and return
        # a dummy User in the response.
        user = User.query.filter(
            sql_and(
                User.active == sql_false(),
                User.failed_login_count <= current_app.config['DM_FAILED_LOGIN_LIMIT']
            )
        ).first()
        encryption.authenticate_user("not a real password", user)
        return jsonify(authorization=False), 404

    elif encryption.authenticate_user(json_payload['password'], user) and user.active:
        user.logged_in_at = datetime.utcnow()
        user.failed_login_count = 0
        db.session.add(user)
        db.session.commit()

        return single_result_response(RESOURCE_NAME, user), 200

    else:
        user.failed_login_count += 1
        db.session.add(user)
        db.session.flush()

        audit_data = {
            'email_address': json_payload['emailAddress'].lower(),
            'failed_login_count': user.failed_login_count,
            'request_id': request.trace_id,
            'span_id': request.span_id,
        }

        audit = AuditEvent(
            audit_type=AuditTypes.user_auth_failed,
            user=json_payload['emailAddress'].lower(),
            data=audit_data,
            db_object=user
        )

        db.session.add(audit)
        db.session.commit()

        return jsonify(authorization=False), 403


@main.route('/users/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    user = User.query.filter(
        User.id == user_id
    ).first_or_404()
    return single_result_response(RESOURCE_NAME, user), 200


@main.route('/users', methods=['GET'])
def list_users():
    user_query = User.query.order_by(User.id)
    page = get_valid_page_or_1()

    # email_address is a primary key
    email_address = request.args.get('email_address')
    if email_address:
        if not is_valid_email_address(email_address):
            abort(400, "email_address must be a valid email address")
        single_user = user_query.filter(
            User.email_address == email_address.lower()
        ).first_or_404()
        return jsonify(
            users=[single_user.serialize()]
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

    personal_data_removed = request.args.get('personal_data_removed')
    if personal_data_removed is not None:
        user_query = user_query.filter(User.personal_data_removed == convert_to_boolean(personal_data_removed))

    user_research_opted_in = request.args.get('user_research_opted_in')
    if user_research_opted_in is not None:
        user_query = user_query.filter(User.user_research_opted_in == convert_to_boolean(user_research_opted_in))

    return paginated_result_response(
        result_name=RESOURCE_NAME,
        results_query=user_query,
        page=page,
        per_page=current_app.config['DM_API_SERVICES_PAGE_SIZE'],
        endpoint='.list_users',
        request_args=request.args
    ), 200


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
        password_changed_at=now,
        user_research_opted_in=False,
    )

    audit_data = {}

    if user.role == "buyer":
        audit_data["qualifyingBuyerEmailDomain"] = buyer_email_address_first_approved_domain(
            BuyerEmailDomain.query.all(),
            user.email_address,
        ).domain_name

    if "supplierId" in json_payload:
        user.supplier_id = json_payload['supplierId']
        #  This key changed from `supplier_id` to `supplierId` to match how we do it everywhere else in August 2018
        audit_data['supplierId'] = user.supplier_id

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

    return single_result_response(RESOURCE_NAME, user), 201


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
        if user.role in ('admin-manager',):
            current_app.logger.warning(
                "{code}: Password reset requested for {user_role} user '{email_hash}'",
                extra={
                    "code": "update_user.password.role_warning",
                    "email_hash": hash_string(user.email_address),
                    "user_role": user.role,
                }
            )
    if 'active' in user_update:
        user.active = user_update['active']
    if 'name' in user_update:
        user.name = user_update['name']
    if 'emailAddress' in user_update:
        user.email_address = user_update['emailAddress']
    if 'phoneNumber' in user_update:
        user.phone_number = user_update['phoneNumber']
    if 'role' in user_update:
        if user.role == 'supplier' and user_update['role'] != user.role:
            user.supplier_id = None
            user_update.pop('supplierId', None)
        if user.role == 'buyer' and user_update['role'] != user.role:
            abort(400, "Can not change a 'buyer' user to a different role.")
        user.role = user_update['role']
    if 'supplierId' in user_update:
        user.supplier_id = user_update['supplierId']
    if 'locked' in user_update and not user_update['locked']:
        user.failed_login_count = 0
    if 'userResearchOptedIn' in user_update:
        user.user_research_opted_in = user_update['userResearchOptedIn']

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
        return single_result_response(RESOURCE_NAME, user), 200
    except (IntegrityError, DataError):
        db.session.rollback()
        abort(400, "Could not update user with: {0}".format(user_update))


@main.route('/users/<int:user_id>/remove-personal-data', methods=['POST'])
def remove_user_personal_data(user_id):
    """ Remove personal data from a user. Looks user up in DB, and removes personal data.

    This should be used to completely remove a user from the Marketplace. Their account will no longer be accessible.
    This is useful for our retention strategy (3 years) and for right to be forgotten requests.
    """
    updater_json = validate_and_return_updater_request()
    user = User.query.filter(
        User.id == user_id
    ).first_or_404()
    user.remove_personal_data()

    audit = AuditEvent(
        audit_type=AuditTypes.update_user,
        user=updater_json['updated_by'],
        db_object=user,
        data={}
    )

    db.session.add(user)
    db.session.add(audit)

    try:
        db.session.commit()
    except (IntegrityError, DataError):
        db.session.rollback()
        abort(400, "Could not remove personal data from user with: ID {0}".format(user.id))

    return single_result_response(RESOURCE_NAME, user), 200


@main.route('/users/export/<framework_slug>', methods=['GET'])
def export_users_for_framework(framework_slug):

    # 400 if framework slug is invalid
    framework = Framework.query.filter(Framework.slug == framework_slug).first()
    if not framework:
        abort(400, 'invalid framework')

    if framework.status == 'coming':
        abort(400, 'framework not yet open')

    suppliers_with_a_complete_service = frozenset(framework.get_supplier_ids_for_completed_service())

    supplier_id_published_service_count = dict(db.session.query(
        Service.supplier_id,
        func.count(Service.id)
    ).filter(
        Service.status == 'published',
        Service.framework_id == framework.id
    ).group_by(
        Service.supplier_id
    ).all())

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

        # This `application_status` logic also exists in suppliers.export_suppliers_for_framework
        application_status = 'application' if (
            declaration_status == 'complete' and
            sf.supplier_id in suppliers_with_a_complete_service and
            company_details_confirmed_if_required_for_framework(framework_slug, sf)
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
            'user_research_opted_in': u.user_research_opted_in,
            'supplier_id': sf.supplier_id,
            'declaration_status': declaration_status,
            'application_status': application_status,
            'framework_agreement': framework_agreement,
            'application_result': application_result,
            'variations_agreed': variations_agreed,
            'published_service_count': supplier_id_published_service_count.get(sf.supplier_id, 0)
        })

    return jsonify(users=user_rows), 200


# Deprecated
@main.route("/users/check-buyer-email", methods=["GET"])
def email_has_valid_buyer_domain():
    email_address = request.args.get('email_address')
    if not email_address:
        abort(400, "'email_address' is a required parameter")

    domain_ok = buyer_email_address_has_approved_domain(BuyerEmailDomain.query.all(), email_address)
    return jsonify(valid=domain_ok), 200


@main.route("/users/check-buyer-email", methods=["POST"])
def email_has_valid_buyer_domain_post():
    json_payload = get_json_from_request()
    json_has_required_keys(json_payload, ['emailAddress'])
    email_address = json_payload['emailAddress']
    domain_ok = buyer_email_address_has_approved_domain(BuyerEmailDomain.query.all(), email_address)
    return jsonify(valid=domain_ok), 200


@main.route("/users/valid-admin-email", methods=["GET"])
def email_is_valid_for_admin_user():
    email_address = request.args.get('email_address')
    if not email_address:
        abort(400, "'email_address' is a required parameter")

    valid = admin_email_address_has_approved_domain(email_address)
    return jsonify(valid=valid), 200
