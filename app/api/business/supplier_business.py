import collections
from app.api.business.validators import SupplierValidator
from app.api.services import suppliers, application_service


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
            'id': 'S000'
        })

    if skip_application_check is False:
        if any([a for a in applications if a.status == 'submitted']):
            validation_result = collections.namedtuple('Notification', ['warnings', 'errors'])
            return validation_result(warnings=[], errors=[])

    return validation_result
