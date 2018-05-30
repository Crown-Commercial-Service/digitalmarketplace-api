from datetime import datetime

from dmapiclient.audit import AuditTypes
from sqlalchemy import func
from sqlalchemy.orm import lazyload
from sqlalchemy.exc import DataError, IntegrityError
from flask import abort, current_app, jsonify, request

from .. import main
from ... import db, encryption
from ...models import (
    AuditEvent,
    BuyerEmailDomain,
    ContactInformation,
    Framework,
    FrameworkLot,
    Lot,
    Service,
    Supplier,
    SupplierFramework,
    User
)
from ...supplier_utils import check_supplier_role
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

    user = User.get_by_email_address(json_payload['emailAddress'].lower())

    if user is None:
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
            'client_ip': request.environ.get('HTTP_X_REAL_IP', request.remote_addr),  # HTTP_X_REAL_IP added by nginx
            'failed_login_count': user.failed_login_count,
            'request_id': request.trace_id,
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


@main.route('/users/export/<framework_slug>', methods=['GET'])
def export_users_for_framework(framework_slug):

    # 400 if framework slug is invalid
    framework = Framework.query.filter(Framework.slug == framework_slug).first()
    if not framework:
        abort(400, 'invalid framework')

    if framework.status == 'coming':
        abort(400, 'framework not yet open')

    suppliers_with_a_complete_service = frozenset(framework.get_supplier_ids_for_completed_service())

    users = db.session.query(
        User.supplier_id, User.name, User.email_address, User.user_research_opted_in
    ).filter(
        User.supplier_id.in_(suppliers_with_a_complete_service)
    ).filter(
        User.active.is_(True)
    )

    users_for_each_supplier = {}
    for u in users:
        user_obj = {
            'email address': u.email_address,
            'user_name': u.name,
            'user_research_opted_in': u.user_research_opted_in,
        }
        # If supplier id key already exists, append the user to that supplier's list
        users_for_each_supplier.setdefault(u.supplier_id, []).append(user_obj)

    lots = db.session.query(FrameworkLot.lot_id, Lot.slug).join(Lot, FrameworkLot.lot_id == Lot.id).filter(
        FrameworkLot.framework_id == framework.id
    ).distinct().all()
    published_service_count_by_supplier_and_lot = {}

    for lot_id, slug in lots:
        published_service_count_by_supplier_and_lot[
            "published_services_count_on_{}_lot".format(slug)
        ] = dict(db.session.query(
            Service.supplier_id,
            func.count(Service.id)
        ).filter(
            Service.status == 'published',
            Service.lot_id == lot_id
        ).group_by(
            Service.supplier_id
        ).group_by(
            Service.lot_id
        ).all())

    supplier_id_published_service_count = {}
    for k, v in published_service_count_by_supplier_and_lot.items():
        for supplier_id, service_count in v.items():
            if supplier_id in supplier_id_published_service_count:
                supplier_id_published_service_count[supplier_id] += service_count
            else:
                supplier_id_published_service_count[supplier_id] = service_count

    supplier_frameworks_and_users = db.session.query(
        SupplierFramework, Supplier, ContactInformation
    ).filter(
        SupplierFramework.supplier_id == Supplier.supplier_id
    ).filter(
        SupplierFramework.framework_id == framework.id
    ).filter(
        ContactInformation.supplier_id == Supplier.supplier_id
    ).options(
        lazyload(SupplierFramework.framework),
        lazyload(SupplierFramework.prefill_declaration_from_framework),
        lazyload(SupplierFramework.framework_agreements),
    ).order_by(
        Supplier.supplier_id,
    ).all()

    supplier_rows = []

    for sf, supplier, ci in supplier_frameworks_and_users:
        # Only export suppliers that have users
        if users_for_each_supplier.get(supplier.supplier_id):

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
                framework_agreement = bool(
                    getattr(sf.current_framework_agreement, 'signed_agreement_returned_at', None)
                )
                variations_agreed = ', '.join(sf.agreed_variations.keys()) if sf.agreed_variations else ''

            supplier_rows.append({
                'users': users_for_each_supplier[supplier.supplier_id],
                'supplier_id': supplier.supplier_id,
                'declaration_status': declaration_status,
                'application_status': application_status,
                'framework_agreement': framework_agreement,
                'application_result': application_result,
                'variations_agreed': variations_agreed,
                'supplier_name': supplier.name,
                'supplier_organisation_size': supplier.organisation_size,
                'duns_number': supplier.duns_number,
                'registered_name': supplier.registered_name,
                'companies_house_number': supplier.companies_house_number,
                "contact_information": {
                    'contact_name': ci.contact_name,
                    'contact_email': ci.email,
                    'contact_phone_number': ci.phone_number,
                    'address_first_line': ci.address1,
                    'address_city': ci.city,
                    'address_postcode': ci.postcode,
                    'address_country': supplier.registration_country,
                },
                "published_services_count": {
                    "digital-outcomes": 0,
                    "digital-specialists": 0,
                    "user-research-studios": 3,
                    "user-research-participants": 0,
                }
            })

    return jsonify(suppliers=[supplier for supplier in supplier_rows]), 200


@main.route("/users/check-buyer-email", methods=["GET"])
def email_has_valid_buyer_domain():
    email_address = request.args.get('email_address')
    if not email_address:
        abort(400, "'email_address' is a required parameter")

    domain_ok = buyer_email_address_has_approved_domain(BuyerEmailDomain.query.all(), email_address)
    return jsonify(valid=domain_ok), 200


@main.route("/users/valid-admin-email", methods=["GET"])
def email_is_valid_for_admin_user():
    email_address = request.args.get('email_address')
    if not email_address:
        abort(400, "'email_address' is a required parameter")

    valid = admin_email_address_has_approved_domain(email_address)
    return jsonify(valid=valid), 200
