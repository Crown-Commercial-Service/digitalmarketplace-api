from app.api.business.validators import ApplicationValidator
from app.models import Application


def test_can_get_errors_with_empty_string():
    application = Application(
        data={
            'tools': '',
            'methodologies': ''
        }
    )
    errors = ApplicationValidator(application).validate_methods()

    assert len(errors) == 2
