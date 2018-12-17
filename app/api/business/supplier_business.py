import collections
from app.api.business.validators import SupplierValidator
from app.api.services import suppliers, application_service


def get_supplier_messages(code, skip_application_check):
    applications = application_service.find(
        supplier_code=code,
        type='edit'
    ).all()

    if any([a for a in applications if a.status == 'saved']):
        validation_result = collections.namedtuple('Notification', ['warnings', 'errors'])
        return validation_result(warnings=[{
            'message': 'You have changes saved in your seller profile. '
                       'Please ensure you go to "Preview and update" and then "Submit updates" '
                       'in your seller profile to finalise your changes, or you can '
                       '"Discard all updates".',
            'severity': 'warning',
            'step': 'start'
        }], errors=[])

    supplier = suppliers.get_supplier_by_code(code)
    validation_result = SupplierValidator(supplier).validate_all()
    if skip_application_check is False:
        if any([a for a in applications if a.status == 'submitted']):
            return None

    return validation_result
