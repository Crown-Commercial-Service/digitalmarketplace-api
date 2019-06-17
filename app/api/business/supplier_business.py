import collections
import pendulum
from app.api.business.validators import SupplierValidator
from app.api.services import (
    suppliers,
    application_service,
    agreement_service,
    key_values_service
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
    signed_agreement = next(iter([sa for sa in supplier.signed_agreements if sa.agreement.is_current is True]), None)
    if not signed_agreement:
        key_value = key_values_service.get_by_key('current_master_agreement')
        if key_value:
            agreement = agreement_service.find(is_current=True).one_or_none()
            agreement_sup = key_value.get('data').get('{}'.format(agreement.id))
            now = pendulum.now('Australia/Canberra').date()
            start_date = (
                pendulum.parse(
                    agreement_sup.get('startDate'),
                    tz='Australia/Canberra'
                ).date()
            )
            message = (
                'From {}, your authorised representative must '
                'accept the new Master Agreement '.format(start_date.strftime('%-d %B %Y'))
                if start_date > now else
                'Your authorised representative must accept the new Master Agreement '
            )
            message = message + (
                'before you can apply for opportunities.'
            )
            validation_result.errors.append({
                'message': message,
                'severity': 'warning' if start_date > now else 'error',
                'step': 'representative',
                'id': 'SB002'
            })

    if skip_application_check is False:
        if any([a for a in applications if a.status == 'submitted']):
            validation_result = collections.namedtuple('Notification', ['warnings', 'errors'])
            return validation_result(warnings=[], errors=[])

    return validation_result
