from app.api.business.validators import SupplierValidator
from app.api.services import suppliers, application_service
from flask import current_app


def get_supplier_messages(code, skip_application_check):
    supplier = suppliers.get_supplier_by_code(code)

    if skip_application_check is False:
        application = application_service.find(
            supplier_code=code,
            status='submitted'
        ).one_or_none()

        if application:
            return None

    return SupplierValidator(supplier).validate_all()
