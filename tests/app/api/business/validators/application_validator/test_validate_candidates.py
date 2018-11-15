import pytest
from app.api.business.validators import ApplicationValidator
from app.models import Application


@pytest.mark.parametrize('recruiter', ['yes', 'both'])
def test_can_get_errors_as_recruiter_with_empty_recruiter_info(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                },
                'recruiter_info': {}
            }
        )).validate_candidates()) == 1


@pytest.mark.parametrize('recruiter', ['yes', 'both'])
def test_can_get_errors_as_recruiter_with_unfilled_recruiter_info(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                },
                'recruiter_info': {
                    'service_1': {}
                }
            })).validate_candidates()) == 5


@pytest.mark.parametrize('recruiter', ['yes', 'both'])
def test_can_get_errors_as_recruiter_with_no_matching_service(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                },
                'recruiter_info': {
                    'service_2': {}
                }
            })).validate_candidates()) == 1


@pytest.mark.parametrize('recruiter', ['yes', 'both'])
def test_can_get_errors_as_recruiter_with_no_recruiter_info(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                }
            })).validate_candidates()) == 1


@pytest.mark.parametrize('recruiter', ['yes', 'both'])
def test_for_no_errors_as_recruiter_with_filled_recruiter_info(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                },
                'recruiter_info': {
                    'service_1': {
                        'database_size': '1',
                        'active_candidates': '2',
                        'margin': '3',
                        'markup': '4',
                        'placed_candidates': '5'
                    }
                }
            })).validate_candidates()) == 0


def test_for_no_errors_as_non_recruiter_with_no_recruiter_info():
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': 'no',
                'services': {
                    'service_1': True
                }
            })).validate_candidates()) == 0
