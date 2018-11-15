from app.api.business.validators import ApplicationValidator
from app.models import Application


def test_can_get_errors_with_empty_string():
    application = Application(
        data={
            'representative': '',
            'email': '',
            'phone': '',
            'contact_name': '',
            'contact_email': '',
            'contact_phone': ''
        }
    )
    errors = ApplicationValidator(application).validate_contacts()

    assert len(errors) == 6
