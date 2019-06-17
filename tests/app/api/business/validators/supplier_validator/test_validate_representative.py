from app.api.business.validators import SupplierValidator
from app.models import Supplier


def test_can_get_errors_with_empty_string():
    supplier = Supplier(
        data={
            'representative': '',
            'email': '',
            'phone': ''
        }
    )
    errors = SupplierValidator(supplier).validate_representative()

    assert len(errors) == 3


def test_with_no_at_in_email():
    supplier = Supplier(
        data={
            'representative': 'foo bar',
            'email': 'ab.cm',
            'phone': '0123456789'
        }
    )
    errors = SupplierValidator(supplier).validate_representative()

    assert len(errors) == 1


def test_with_too_many_at_in_email():
    supplier = Supplier(
        data={
            'representative': 'foo bar',
            'email': 'a@@b.cm',
            'phone': '0123456789'
        }
    )
    errors = SupplierValidator(supplier).validate_representative()

    assert len(errors) == 1


def test_with_invalid_phone():
    supplier = Supplier(
        data={
            'representative': 'foo bar',
            'email': 'a@b.cm',
            'phone': 'asd33333f'
        }
    )
    errors = SupplierValidator(supplier).validate_representative()
    assert len(errors) == 1
    assert 'S013-phone' in [e['id'] for e in errors]

    supplier = Supplier(
        data={
            'representative': 'foo bar',
            'email': 'a@b.cm',
            'phone': 'aaaaa11111'
        }
    )
    errors = SupplierValidator(supplier).validate_representative()
    assert len(errors) == 1
    assert 'S013-phone' in [e['id'] for e in errors]

    supplier = Supplier(
        data={
            'representative': 'foo bar',
            'email': 'a@b.cm',
            'phone': '11111aaaaa'
        }
    )
    errors = SupplierValidator(supplier).validate_representative()
    assert len(errors) == 1
    assert 'S013-phone' in [e['id'] for e in errors]


def test_with_valid_data():
    supplier = Supplier(
        data={
            'representative': 'foo bar',
            'email': 'a@b.cm',
            'phone': '0123456789'
        }
    )
    errors = SupplierValidator(supplier).validate_representative()

    assert len(errors) == 0

    supplier = Supplier(
        data={
            'representative': 'foo bar',
            'email': 'a@b.cm',
            'phone': '+(0)123456789'
        }
    )
    errors = SupplierValidator(supplier).validate_representative()

    assert len(errors) == 0
