import pytest
from app.api.business.validators import ApplicationValidator
from app.models import Application


@pytest.mark.parametrize('recruiter', ['yes', 'both'])
def test_can_get_errors_as_recruiter_with_empty_candidate_info(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'candidates': {}
            }
        )).validate_candidates()) == 1


@pytest.mark.parametrize('recruiter', ['yes', 'both'])
def test_can_get_errors_as_recruiter_with_no_candidate_info(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter
            })).validate_candidates()) == 1


@pytest.mark.parametrize('recruiter', ['yes', 'both'])
def test_for_no_errors_as_recruiter_with_filled_candidate_info(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'candidates': {
                    'database_size': '1',
                    'active_candidates': '2',
                    'margin': '3.6',
                    'markup': '4',
                    'placed_candidates': '5'
                }
            })).validate_candidates()) == 0


def test_for_no_errors_as_non_recruiter_with_no_candidate_info():
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': 'no'
            })).validate_candidates()) == 0


@pytest.mark.parametrize('recruiter', ['yes', 'both'])
def test_can_get_errors_as_recruiter_with_no_whole_numbers(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'candidates': {
                    'database_size': '1.2',
                    'active_candidates': 'abc',
                    'margin': '3.4',
                    'markup': '4.5',
                    'placed_candidates': None
                }
            })).validate_candidates()) == 3


@pytest.mark.parametrize('recruiter', ['yes', 'both'])
def test_can_get_errors_as_recruiter_with_no_whole_or_decimal_numbers(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'candidates': {
                    'database_size': '1',
                    'active_candidates': '2',
                    'margin': '3.4 percent',
                    'markup': '4.5%',
                    'placed_candidates': '5'
                }
            })).validate_candidates()) == 2
