from app.api.business.validators import SupplierValidator
from app.models import Supplier

def test_can_zero_errors_for_sa_past_date_and_no_licence_number():
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