from app.api.business.validators import ApplicationValidator
from app.models import Application


def test_can_get_errors_with_unfilled_product():
    assert len(ApplicationValidator(
        Application(
            data={
                'products': {
                    '0': {}
                }
            }
        )).validate_products()) == 5


def test_for_no_errors_with_empty_product():
    assert len(ApplicationValidator(
        Application(
            data={
                'products': {}
            })).validate_products()) == 0

    assert len(ApplicationValidator(
        Application(data={})).validate_products()) == 0


def test_for_no_errors_with_filled_product():
    assert len(ApplicationValidator(
        Application(
            data={
                'products': {
                    '0': {
                        'name': '1',
                        'summary': '2',
                        'website': 'http://unsafe.site',
                        'pricing': 'https://www.google.com',
                        'support': 'http://www.google.com'
                    }
                }
            })).validate_products()) == 0


def test_for_errors_with_bad_url():
    assert len(ApplicationValidator(
        Application(
            data={
                'products': {
                    '0': {
                        'name': '1',
                        'summary': '2',
                        'website': '3',
                        'pricing': '4',
                        'support': '5'
                    }
                }
            })).validate_products()) == 3
