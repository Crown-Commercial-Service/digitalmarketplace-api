from app.api.business.validators import ApplicationValidator
from app.models import Application


def test_can_get_error_when_no_documents():
    application = Application(
        data={}
    )
    errors = ApplicationValidator(application).validate_documents()

    assert len(errors) == 1


def test_can_get_error_for_expired_documents():
    application = Application(
        data={
            'documents': {
                'liability': {
                    'filename': 'test.pdf',
                    'expiry': '2018/01/01'
                },
                'workers': {
                    'filename': 'test.pdf',
                    'expiry': '2018/01/01'
                },
                'financial': {
                    'filename': 'test.pdf'
                }
            }
        }
    )
    errors = ApplicationValidator(application).validate_documents()

    assert len(errors) == 2


def test_can_get_error_for_no_filename():
    application = Application(
        data={
            'documents': {
                'liability': {
                    'filename': '',
                    'expiry': '2018/01/01'
                },
                'workers': {
                    'filename': '',
                    'expiry': '2018/01/01'
                },
                'financial': {
                    'filename': ''
                }
            }
        }
    )
    errors = ApplicationValidator(application).validate_documents()

    assert len(errors) == 5
