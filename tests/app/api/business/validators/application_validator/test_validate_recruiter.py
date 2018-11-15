from app.api.business.validators import ApplicationValidator
from app.models import Application


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
