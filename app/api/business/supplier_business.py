from app.api.business.validators.supplier_validator import SupplierValidator
from app.api.services import suppliers


def get_supplier_validation_result(code):
    supplier = suppliers.get_supplier_by_code(code)
    validation_result = SupplierValidator(supplier).validate_all()
    return validation_result
