from app import db, encryption
from app.models import Application, AuditEvent, AuditTypes, User, Framework, UserFramework
from datetime import datetime
from flask import current_app, request, jsonify
from sqlalchemy.exc import DataError, InvalidRequestError, IntegrityError
from sqlalchemy.orm import noload
from app.emails.users import send_existing_application_notification, send_existing_seller_notification
from app.api.applications import create_application
from app.emails.users import send_new_user_onboarding_email
from app.tasks import publish_tasks


def add_user(data):
    if data is None:
        raise DataError('create_user requires a data arg')

    name = data.get('name')
    password = data.get('password')
    role = data.get('user_type')
    email_address = data.get('email_address', None)
    framework_slug = data.get('framework', 'digital-marketplace')

    if email_address is None:
        email_address = data.get('emailAddress', None)

    if 'hashpw' in data and not data['hashpw']:
        password = password
    else:
        password = encryption.hashpw(password)

    if role == 'seller':
        role = 'applicant'

    now = datetime.utcnow()
    user = User(
        email_address=email_address.lower(),
        phone_number=data.get('phoneNumber', None),
        name=name,
        role=role,
        password=password,
        active=True,
        created_at=now,
        updated_at=now,
        password_changed_at=now
    )

    audit_data = {}

    if "supplier_code" in data:
        user.supplier_code = data['supplier_code']
        audit_data['supplier_code'] = user.supplier_code

    if user.role == 'supplier' and user.supplier_code is None:
        raise ValueError("'supplier_code' is required for users with 'supplier' role")

    if user.role != 'supplier' and user.supplier_code is not None:
        raise ValueError("'supplier_code' is only valid for users with 'supplier' role, not '{}'".format(user.role))

    if "application_id" in data:
        user.application_id = data['application_id']
    elif user.supplier_code is not None:
        appl = Application.query.filter_by(supplier_code=user.supplier_code).first()
        user.application_id = appl and appl.id or None

    if user.role == 'applicant' and user.application_id is None:
        raise ValueError("'application id' is required for users with 'applicant' role")
    elif user.role != 'applicant' and user.role != 'supplier' and user.application_id is not None:
        raise ValueError(
            "'application_id' is only valid for users with applicant' or 'supplier' role, not '{}'".format(user.role))

    db.session.add(user)
    db.session.flush()

    framework = Framework.query.filter(Framework.slug == framework_slug).first()
    db.session.add(UserFramework(user_id=user.id, framework_id=framework.id))

    audit = AuditEvent(
        audit_type=AuditTypes.create_user,
        user=email_address.lower(),
        data=audit_data,
        db_object=user
    )

    db.session.add(audit)
    db.session.commit()

    user = db.session.query(User).options(noload('*')).filter(User.id == user.id).one_or_none()
    publish_tasks.user.delay(user.serialize(), 'created')

    return user


def is_duplicate_user(email_address):
    domain = email_address.split('@')[-1]
    if domain in current_app.config['GENERIC_EMAIL_DOMAINS']:
        return False

    supplier_code = db.session.execute("""
        select distinct(supplier_code) from vuser
        where email_domain = :domain
    """, {'domain': domain}).fetchone()

    if (supplier_code and supplier_code[0]):
        send_existing_seller_notification(email_address, supplier_code[0])
        duplicate_audit_event(email_address, {'supplier_code': supplier_code[0]})
        return True

    application_id = db.session.execute("""
        select distinct(application_id) from vuser
        where email_domain = :domain
    """, {'domain': domain}).fetchone()

    if (application_id and application_id[0]):
        duplicate_audit_event(email_address, {'application_id': application_id[0]})
        send_existing_application_notification(
            email_address=email_address,
            application_id=application_id[0])
        return True

    return False


def duplicate_audit_event(email_address, data):
    audit = AuditEvent(
        audit_type=AuditTypes.duplicate_supplier,
        user=email_address,
        data=data,
        db_object=None
    )

    db.session.add(audit)
    db.session.commit()


def update_user_details(**kwargs):
    """
        Update a user. Looks user up in DB, and updates where necessary.
    """

    user_id = kwargs.get('user_id', None)

    user = User.query.filter(User.id == user_id).first()

    if user is None:
        raise ValueError("Unable to modify user. User with id {} does not exist".format(user_id))

    if kwargs.get('password', None) is not None:
        user.password = encryption.hashpw(kwargs['password'])
        user.password_changed_at = datetime.utcnow()
    if kwargs.get('active', None) is not None:
        user.active = kwargs['active']
    if kwargs.get('name', None) is not None:
        user.name = kwargs['name']
    if kwargs.get('email_address', None) is not None:
        user.email_address = kwargs['email_address']
    if kwargs.get('role', None) is not None:
        if user.role == 'supplier' and kwargs['role'] != user.role:
            user.supplier_code = None
            kwargs.pop('supplierCode', None)
        user.role = kwargs['role']
    if kwargs.get('supplierCode', None) is not None:
        user.supplier_code = kwargs['supplierCode']
    if kwargs.get('application_id', None) is not None:
        user.application_id = kwargs['application_id']
    if kwargs.get('locked', None) and not kwargs['locked']:
        user.failed_login_count = 0
    if kwargs.get('termsAcceptedAt', None) is not None:
        user.terms_accepted_at = kwargs['termsAcceptedAt']

    check_supplier_role(user.role, user.supplier_code)

    update_data = {
        "user_id": user_id,
        "email_address": kwargs.get('email_address', None)
    }

    audit = AuditEvent(
        audit_type=AuditTypes.update_user,
        user=kwargs.get('updated_by', 'no user data'),
        data={
            'user': user.email_address,
            'update': update_data
        },
        db_object=user
    )

    db.session.add(user)
    db.session.add(audit)

    db.session.commit()

    return user


def check_supplier_role(role, supplier_code):
    if role == 'supplier' and supplier_code is None:
        raise ValueError("'supplier_code' is required for users with 'supplier' role")
    elif role != 'supplier' and supplier_code is not None:
        raise("'supplier_code' is only valid for users with 'supplier' role, not '{}'".format(role))


def create_user(user_type=None, name=None, email_address=None, password=None, framework=None):
    if not user_type or not name or not email_address or not password or not framework:
        return jsonify(
            application_id=user.application_id,
            message="Missing input"
        ), 400

    user = User.query.filter(
        User.email_address == email_address.lower()).first()

    if user is not None:
        return jsonify(
            application_id=user.application_id,
            message="A user with the email address '{}' already exists".format(email_address)
        ), 409

    if user_type not in ['seller', 'buyer']:
        return jsonify(message='An invalid user type was passed to create new user api'), 400

    user_data = {
        'user_type': user_type,
        'name': name,
        'email_address': email_address,
        'password': password,
        'framework': framework
    }

    if user_type == "seller":
        try:
            application = create_application(email_address=email_address, name=name)
            user_data['application_id'] = application.id

        except (InvalidRequestError, IntegrityError):
            return jsonify(message="An application with this email address already exists"), 409

    try:
        user = add_user(data=user_data)

        send_new_user_onboarding_email(
            name=user.name,
            email_address=user.email_address,
            user_type=user_type,
            framework=framework
        )

        user = {
            k: v for k, v in user._dict.items() if k in [
                'name', 'email_address', 'application_id', 'role', 'supplier_code']
        }

        return jsonify(user)

    except IntegrityError as error:
        return jsonify(message=error.message), 409

    except Exception as error:
        return jsonify(message=error.message), 400
