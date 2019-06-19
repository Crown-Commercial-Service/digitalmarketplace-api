import rollbar
import pendulum
from app.api.services import (
    key_values_service,
    suppliers,
    users,
    user_claims_service,
    agreement_service,
    signed_agreement_service,
    audit_service,
    audit_types
)
from app.models import SignedAgreement
from app.api.business.validators import SupplierValidator
from app.tasks import publish_tasks
from app.emails.seller_edit import (
    send_notify_auth_rep_email,
    send_decline_master_agreement_email,
    send_team_member_account_activation_email
)
from app.api.business.errors import (
    DeletedError,
    NotFoundError,
    UnauthorisedError,
    ValidationError
)
from app.api.business.agreement_business import (
    get_current_agreement,
    get_new_agreement,
    has_signed_current_agreement
)


def accept_agreement(user_info):
    supplier_code = user_info.get('supplier_code')
    email_address = user_info.get('email_address')
    user_id = user_info.get('user_id')

    supplier = suppliers.get_supplier_by_code(supplier_code)
    mandatory_supplier_checks(supplier)

    if email_address != supplier.data.get('email'):
        raise UnauthorisedError('Unauthorised to accept agreement')

    agreement = get_current_agreement()
    already_signed = signed_agreement_service.first(agreement_id=agreement['agreementId'], supplier_code=supplier_code)
    if already_signed:
        raise ValidationError('Already signed agreement')

    signed_agreement = SignedAgreement(
        agreement_id=agreement['agreementId'],
        user_id=user_id,
        signed_at=pendulum.now('Australia/Canberra'),
        supplier_code=supplier_code
    )
    signed_agreement_service.save(signed_agreement)

    publish_tasks.supplier.delay(
        publish_tasks.compress_supplier(supplier),
        'accepted_agreement',
        updated_by=email_address
    )

    audit_service.log_audit_event(
        audit_type=audit_types.accepted_master_agreement,
        user=email_address,
        data={
            'supplierCode': supplier.code,
            'supplierData': supplier.data
        },
        db_object=supplier)


def decline_agreement(user_info):
    supplier_code = user_info.get('supplier_code')
    email_address = user_info.get('email_address')

    supplier = suppliers.get_supplier_by_code(supplier_code)
    mandatory_supplier_checks(supplier)

    if email_address != supplier.data.get('email'):
        raise UnauthorisedError('Unauthorised to decline agreement')

    supplier_users = users.find(supplier_code=supplier_code).all()
    supplier.status = 'deleted'
    for user in supplier_users:
        user.active = False
        users.add_to_session(user)

    users.commit_changes()
    suppliers.save(supplier)

    send_decline_master_agreement_email(supplier.code)

    publish_tasks.supplier.delay(
        publish_tasks.compress_supplier(supplier),
        'declined_agreement',
        updated_by=email_address
    )

    audit_service.log_audit_event(
        audit_type=audit_types.declined_master_agreement,
        user=email_address,
        data={
            'supplierCode': supplier.code,
            'supplierData': supplier.data
        },
        db_object=supplier)


def get_supplier_edit_info(user_info):
    supplier_code = user_info.get('supplier_code')
    email_address = user_info.get('email_address')

    supplier = suppliers.get_supplier_by_code(supplier_code)

    agreementStatus = get_agreement_status(supplier, user_info)
    return {
        'supplier': {
            'name': supplier.name,
            'code': supplier.code,
            'abn': supplier.abn,
            'data': {
                'representative': supplier.data.get('representative'),
                'email': supplier.data.get('email'),
                'phone': supplier.data.get('phone')
            }
        },
        'agreementStatus': agreementStatus
    }


def get_agreement_status(supplier, user_info):
    email_address = user_info.get('email_address')

    show_agreement = False
    can_sign_agreement = False
    signed_agreement = False
    can_user_sign_agreement = False
    new_agreement = None
    start_date = pendulum.now('Australia/Canberra').date()

    agreement = get_current_agreement()
    new_agreement = get_new_agreement()
    signed = has_signed_current_agreement(supplier)

    if agreement:
        now = pendulum.now('Australia/Canberra').date()
        start_date = (
            pendulum.parse(
                agreement.get('startDate'),
                tz='Australia/Canberra'
            ).date()
        )
        show_agreement = True
        can_sign_agreement = True
        signed_agreement = True if signed else False

    can_user_sign_agreement = (
        True
        if supplier.data.get('email') == email_address
        else False
    )

    return {
        'show': show_agreement,
        'canSign': can_sign_agreement,
        'canUserSign': can_user_sign_agreement,
        'signed': signed_agreement,
        'startDate': start_date.strftime('%Y-%m-%d'),
        'currentAgreement': agreement,
        'newAgreement': new_agreement
    }


def update_supplier(data, user_info):
    supplier_code = user_info.get('supplier_code')
    email_address = user_info.get('email_address')

    supplier = suppliers.find(code=supplier_code).one_or_none()
    mandatory_supplier_checks(supplier)

    whitelist_fields = ['representative', 'email', 'phone']
    for wf in whitelist_fields:
        if wf not in data.get('data'):
            raise ValidationError('{} is not recognised'.format(wf))

    if 'email' in data.get('data'):
        email = data['data']['email']
        data['data']['email'] = email.encode('utf-8').lower()

    supplier.update_from_json(data.get('data'))

    messages = SupplierValidator(supplier).validate_representative('representative')
    if len([m for m in messages if m.get('severity', '') == 'error']) > 0:
        raise ValidationError(',\n'.join([m.get('message') for m in messages if m.get('severity', '') == 'error']))

    suppliers.save(supplier)

    publish_tasks.supplier.delay(
        publish_tasks.compress_supplier(supplier),
        'updated',
        updated_by=email_address
    )

    audit_service.log_audit_event(
        audit_type=audit_types.update_supplier,
        user=email_address,
        data={
            'supplierCode': supplier.code,
            'supplierData': supplier.data
        },
        db_object=supplier)

    process_auth_rep_email(supplier, data, user_info)


def process_auth_rep_email(supplier, data, user_info):
    email_address = supplier.data.get('email', '').encode('utf-8')
    user = users.find(email_address=email_address).one_or_none()
    if not user:
        framework = data.get('framework', 'digital-marketplace')
        user_data = {
            'name': supplier.data.get('representative'),
            'user_type': 'seller',
            'framework': framework,
            'supplier_code': supplier.code
        }
        claim = user_claims_service.make_claim(type='signup', email_address=email_address, data=user_data)
        if not claim:
            return jsonify(message="There was an issue completing the signup process."), 500

        send_team_member_account_activation_email(
            token=claim.token,
            email_address=email_address,
            framework=framework,
            user_name=user_info.get('name'),
            supplier_name=supplier.name
        )


def notify_auth_rep(user_info):
    supplier_code = user_info.get('supplier_code')
    email_address = user_info.get('email_address')

    supplier = suppliers.get_supplier_by_code(supplier_code)
    mandatory_supplier_checks(supplier)

    send_notify_auth_rep_email(supplier.code)

    audit_service.log_audit_event(
        audit_type=audit_types.notify_auth_rep_accept_master_agreement,
        user=email_address,
        data={
            'supplierCode': supplier.code,
            'supplierData': supplier.data
        },
        db_object=supplier)


def mandatory_supplier_checks(supplier):
    if not supplier:
        raise NotFoundError("Invalid supplier code '{}'".format(supplier_code))

    if supplier.status == 'deleted':
        raise DeletedError('Cannot edit a {} supplier'.format(supplier.status))
