from app.api.business.validators import SupplierValidator
from app.models import Supplier

def test_get_no_errors_from_expiried_sa_and_empty_licence_number():
    supplier = Supplier(
        data={
            'recruiter': 'yes',
            'labourHire': {
                'sa': {
                    'expiry': '01/01/2019'
                }
            }
        }
    )
    errors = SupplierValidator(supplier).validate_recruiter()

    assert len(errors) == 0

def test_can_get_error_for_no_vic_licence_number():
    supplier = Supplier(
        data={
            'recruiter': 'yes',
            'labourHire': {
                'vic': {
                    'expiry': '01/01/2050'
                }
            }
        }
    )
    errors = SupplierValidator(supplier).validate_recruiter()

    assert len(errors) == 1