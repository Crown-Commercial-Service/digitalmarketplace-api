import collections
import pendulum
from app.api.business.validators import SupplierValidator
from app.api.services import (
    suppliers,
    application_service,
    agreement_service,
    key_values_service
)
from app.api.business.agreement_business import (
    get_new_agreement,
    has_signed_current_agreement,
    get_current_agreement
)


def get_supplier_messages(code, skip_application_check):
    applications = application_service.find(
        supplier_code=code,
        type='edit'
    ).all()

    supplier = suppliers.get_supplier_by_code(code)
    validation_result = SupplierValidator(supplier).validate_all()

    if any([a for a in applications if a.status == 'saved']):
        validation_result.warnings.append({
            'message': 'You have saved updates on your profile. '
                       'You must submit these changes to the Marketplace for review. '
                       'If you did not make any changes, select \'Discard all updates\'.',
            'severity': 'warning',
            'step': 'update',
            'id': 'SB001'
        })

    if not skip_application_check:
        if any([a for a in applications if a.status == 'submitted']):
            del validation_result.warnings[:]
            del validation_result.errors[:]

    new_master_agreement = get_new_agreement()
    if new_master_agreement:
        start_date = pendulum.parse(new_master_agreement['startDate'], tz='Australia/Canberra').date()
        message = (
            'From {}, your authorised representative must '
            'accept the new Master Agreement '
            'before you can apply for opportunities.'
        ).format(start_date.strftime('%-d %B %Y'))

        validation_result.warnings.append({
            'message': message,
            'severity': 'warning',
            'step': 'representative',
            'id': 'SB002'
        })
    else:
        if not has_signed_current_agreement(supplier):
            current_agreement = get_current_agreement()
            if current_agreement:
                start_date = pendulum.parse(current_agreement['startDate'], tz='Australia/Canberra').date()
                message = (
                    'Your authorised representative {must accept the new Master Agreement} '
                    'before you can apply for opportunities.'
                )
                validation_result.errors.append({
                    'message': message,
                    'severity': 'error',
                    'step': 'representative',
                    'id': 'SB002',
                    'links': {
                        'must accept the new Master Agreement': '/2/seller-edit/{}/representative'.format(code)
                    }
                })

    return validation_result
