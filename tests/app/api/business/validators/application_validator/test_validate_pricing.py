import pytest
from app.api.business.validators import ApplicationValidator
from app.models import Application


@pytest.mark.parametrize('recruiter', ['no', 'both'])
def test_can_get_errors_as_non_recruiter_with_none_max_price(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                },
                'pricing': {
                    'service_1': {
                        'maxPrice': None
                    }
                }
            }
        )).validate_pricing()) == 1


@pytest.mark.parametrize('recruiter', ['no', 'both'])
def test_can_get_errors_as_non_recruiter_with_no_max_price(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                },
                'pricing': {
                    'service_1': {}
                }
            })).validate_pricing()) == 1


@pytest.mark.parametrize('recruiter', ['no', 'both'])
def test_can_get_errors_as_non_recruiter_with_no_matching_service(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                },
                'pricing': {
                    'service_2': {}
                }
            })).validate_pricing()) == 1


@pytest.mark.parametrize('recruiter', ['no', 'both'])
def test_can_get_errors_as_non_recruiter_with_no_pricing(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                }
            })).validate_pricing()) == 1


def test_for_no_errors_as_recruiter_with_no_pricing():
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': 'yes',
                'services': {
                    'service_1': True
                }
            })).validate_pricing()) == 0
