from app.api.business.validators import ApplicationValidator
from app.models import Application
from datetime import date, timedelta


def test_can_get_errors_with_none_recruiter():
    application = Application(
        data={
            'recruiter': None
        }
    )
    errors = ApplicationValidator(application).validate_recruiter()

    assert len(errors) == 1


def test_can_get_errors_with_no_recruiter():
    application = Application(
        data={
        }
    )
    errors = ApplicationValidator(application).validate_recruiter()

    assert len(errors) == 1


def test_no_errors_for_valid_recruiter():
    application = Application(
        data={
            'recruiter': 'yes'
        }
    )
    errors = ApplicationValidator(application).validate_recruiter()

    assert len(errors) == 0


def test_can_get_errors_for_past_date_and_no_licence_number():
    application = Application(
        data={
            'recruiter': 'yes',
            'labourHire': {
                'vic': {
                    'expiry': '01/01/2019'
                },
                'act': {
                    'expiry': '01/01/2019'
                }
            }
        }
    )
    errors = ApplicationValidator(application).validate_recruiter()

    assert len(errors) == 4


def test_get_no_errors_for_sa_past_date_and_no_licence_number():
    application = Application(
        data={
            'recruiter': 'yes',
            'labourHire': {
                'sa': {
                    'expiry': '01/01/2019'
                }
            }
        }
    )
    errors = ApplicationValidator(application).validate_recruiter()

    assert len(errors) == 0


def test_can_get_error_for_no_licence_number():
    expiry_date = date.today() + timedelta(days=10)
    expiry = '{}-{}-{}'.format(expiry_date.year, expiry_date.month, expiry_date.day)
    application = Application(
        data={
            'recruiter': 'yes',
            'labourHire': {
                'vic': {
                    'expiry': expiry
                },
                'act': {
                    'expiry': expiry
                }
            }
        }
    )
    errors = ApplicationValidator(application).validate_recruiter()

    assert len(errors) == 2


def test_get_no_errors_from_sa_empty_licence_number():
    expiry_date = date.today() + timedelta(days=10)
    expiry = '{}-{}-{}'.format(expiry_date.year, expiry_date.month, expiry_date.day)
    application = Application(
        data={
            'recruiter': 'yes',
            'labourHire': {
                'sa': {
                    'expiry': expiry
                }
            }
        }
    )
    errors = ApplicationValidator(application).validate_recruiter()

    assert len(errors) == 0


def test_can_get_error_for_no_expiry():
    application = Application(
        data={
            'recruiter': 'yes',
            'labourHire': {
                'vic': {
                    'licenceNumber': 'foobar-licence'
                },
                'act': {
                    'licenceNumber': 'foobar-licence'
                }
            }
        }
    )
    errors = ApplicationValidator(application).validate_recruiter()

    assert len(errors) == 2


def test_can_get_no_errors_for_sa_no_expiry():
    application = Application(
        data={
            'recruiter': 'yes',
            'labourHire': {
                'sa': {
                    'licenceNumber': 'foobar-licence'
                }
            }
        }
    )
    errors = ApplicationValidator(application).validate_recruiter()

    assert len(errors) == 0


def test_valid_for_recruiter_and_labour_hire():
    expiry_date = date.today() + timedelta(days=10)
    expiry = '{}-{}-{}'.format(expiry_date.year, expiry_date.month, expiry_date.day)
    application = Application(
        data={
            'recruiter': 'yes',
            'labourHire': {
                'vic': {
                    'expiry': expiry,
                    'licenceNumber': 'foobar-licence'
                },
                'act': {
                    'expiry': expiry,
                    'licenceNumber': 'foobar-licence'
                }
            }
        }
    )
    errors = ApplicationValidator(application).validate_recruiter()

    assert len(errors) == 0
