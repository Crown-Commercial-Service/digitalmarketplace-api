from app.api.business.validators import SupplierValidator
from app.models import Supplier


def test_get_no_errors_from_expired_sa_and_empty_licence_number():
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


def test_get_no_errors_from_sa_empty_licence_number():
    supplier = Supplier(
        data={
            'recruiter': 'yes',
            'labourHire': {
                'sa': {
                    'expiry': '01/01/2050'
                }
            }
        }
    )
    errors = SupplierValidator(supplier).validate_recruiter()

    assert len(errors) == 0


def test_can_get_error_for_vic_licence_number():
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


def test_can_get_no_errors_for_sa_no_expiry():
    supplier = Supplier(
        data={
            'recruiter': 'yes',
            'labourHire': {
                'sa': {
                    'licenceNumber': 'foobar-licence'
                }
            }
        }
    )
    errors = SupplierValidator(supplier).validate_recruiter()

    assert len(errors) == 0


def test_valid_for_recruiter_and_labour_hire_vic():
    supplier = Supplier(
        data={
            'recruiter': 'yes',
            'labourHire': {
                'vic': {
                    'expiry': '01/01/2050',
                    'licenceNumber': 'foobar-licence'
                }
            }
        }
    )
    errors = SupplierValidator(supplier).validate_recruiter()

    assert len(errors) == 0
