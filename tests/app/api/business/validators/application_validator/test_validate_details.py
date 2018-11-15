from app.api.business.validators import ApplicationValidator
from app.models import Application


def test_can_get_errors_with_empty_string():
    application = Application(
        data={
            'number_of_employees': ''
        }
    )
    errors = ApplicationValidator(application).validate_details()

    assert len(errors) == 1
