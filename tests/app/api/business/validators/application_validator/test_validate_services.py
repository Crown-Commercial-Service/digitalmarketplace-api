from app.api.business.validators import ApplicationValidator
from app.models import Application


def test_can_get_errors_with_none_services():
    application = Application(
        data={
            'services': None
        }
    )
    errors = ApplicationValidator(application).validate_services()

    assert len(errors) == 1


def test_can_get_errors_with_no_services():
    application = Application(
        data={
        }
    )
    errors = ApplicationValidator(application).validate_services()

    assert len(errors) == 1
