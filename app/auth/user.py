from app import db, encryption
from app.models import Application, AuditEvent, AuditTypes, User
from datetime import datetime
from flask import current_app
from sqlalchemy.exc import DataError
from app.emails.users import send_existing_application_notification


def create_user(data):
    if data is None:
        raise DataError('create_user requires a data arg')

    name = data.get('name')
    password = data.get('password')
    role = data.get('user_type')
    email_address = data.get('email_address', None)
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

    audit = AuditEvent(
        audit_type=AuditTypes.create_user,
        user=email_address.lower(),
        data=audit_data,
        db_object=user
    )

    db.session.add(audit)
    db.session.commit()

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
