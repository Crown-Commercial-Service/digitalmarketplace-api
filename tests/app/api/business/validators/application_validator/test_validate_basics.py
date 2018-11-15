from app.api.business.validators import ApplicationValidator
from app.models import Application


def test_can_get_errors_with_empty_string():
    application = Application(
        data={
            'name': '',
            'abn': '',
            'summary': '',
            'website': '',
            'addresses': [{
                'address_line': '',
                'suburb': '',
                'state': '',
                'postal_code': ''
            }]
        }
    )
    errors = ApplicationValidator(application).validate_basics()

    assert len(errors) == 8


def test_can_get_errors_with_space():
    application = Application(
        data={
            'name': ' ',
            'abn': '  ',
            'summary': '   ',
            'website': '    ',
            'addresses': [{
                'address_line': '    ',
                'suburb': '    ',
                'state': '    ',
                'postal_code': '    '
            }]
        }
    )
    errors = ApplicationValidator(application).validate_basics()

    assert len(errors) == 8


def test_can_get_errors_with_nulls():
    application = Application(
        data={
            'name': None,
            'abn': None,
            'summary': None,
            'website': None,
            'addresses': [{
                'address_line': None,
                'suburb': None,
                'state': None,
                'postal_code': None
            }]
        }
    )
    errors = ApplicationValidator(application).validate_basics()

    assert len(errors) == 8


def test_can_get_errors_with_incorrect_url():
    application = Application(
        data={
            'name': None,
            'abn': None,
            'summary': None,
            'website': 'foobar',
            'addresses': [{
                'address_line': None,
                'suburb': None,
                'state': None,
                'postal_code': None
            }],
            'linkedin': 'ftp://'
        }
    )
    errors = ApplicationValidator(application).validate_basics()

    assert len(errors) == 9


def test_can_get_errors_when_not_defined():
    application = Application(
        data={}
    )
    errors = ApplicationValidator(application).validate_basics()

    assert len(errors) == 5


def test_for_no_errors_with_correct_application():
    application = Application(
        data={
            'name': 'Jogn',
            'abn': '123',
            'summary': 'summary',
            'website': 'https://',
            'addresses': [{
                'address_line': '8 some street',
                'suburb': 'City',
                'state': 'ACT',
                'postal_code': '2600'
            }],
            'linkedin': 'http://'
        }
    )
    errors = ApplicationValidator(application).validate_basics()

    assert len(errors) == 0
