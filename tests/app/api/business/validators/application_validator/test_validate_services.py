from app.api.business.validators import ApplicationValidator
from app.models import Application


def test_can_get_errors_with_none_services():
    application = Application(
        data={
            'recruiter': 'yes',
            'services': None
        }
    )
    errors = ApplicationValidator(application).validate_services()

    assert len(errors) == 1


def test_can_get_errors_with_no_services():
    application = Application(
        data={
            'recruiter': 'yes'
        }
    )
    errors = ApplicationValidator(application).validate_services()

    assert len(errors) == 1


def test_get_no_errors_with_no_services():
    application = Application(
        data={
            'recruiter': 'no'
        }
    )
    errors = ApplicationValidator(application).validate_services()

    assert len(errors) == 0
