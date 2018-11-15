import pytest
from app.api.business.validators import ApplicationValidator
from app.models import Application


@pytest.mark.parametrize('recruiter', ['no', 'both'])
def test_can_get_errors_as_non_recruiter_with_empty_case_studies(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                },
                'case_studies': []
            }
        )).validate_case_studies()) == 1


@pytest.mark.parametrize('recruiter', ['no', 'both'])
def test_can_get_errors_as_non_recruiter_with_unfilled_fields(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                },
                'case_studies': [{
                    'title': '',
                    'client': '',
                    'timeframe': '',
                    'roles': '',
                    'opportunity': '',
                    'approach': '',
                    'referee_name': '',
                    'referee_position': '',
                    'referee_contact': '',
                    'referee_email': '',
                    'service': 'service_1'
                }]
            })).validate_case_studies()) == 11


@pytest.mark.parametrize('recruiter', ['no', 'both'])
def test_can_get_errors_as_non_recruiter_with_empty_outcome(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                },
                'case_studies': [{
                    'title': 'value',
                    'client': 'value',
                    'timeframe': 'value',
                    'roles': 'value',
                    'opportunity': 'value',
                    'approach': 'value',
                    'referee_name': 'value',
                    'referee_position': 'value',
                    'referee_contact': 'value',
                    'referee_email': 'value',
                    'service': 'service_1',
                    'outcome': [
                        ''
                    ]
                }]
            })).validate_case_studies()) == 1


@pytest.mark.parametrize('recruiter', ['no', 'both'])
def test_can_get_errors_as_non_recruiter_with_incorrect_url(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                },
                'case_studies': [{
                    'title': 'value',
                    'client': 'value',
                    'timeframe': 'value',
                    'roles': 'value',
                    'opportunity': 'value',
                    'approach': 'value',
                    'referee_name': 'value',
                    'referee_position': 'value',
                    'referee_contact': 'value',
                    'referee_email': 'value',
                    'service': 'service_1',
                    'outcome': [
                        'value'
                    ],
                    'project_links': [
                        'ftp://error.gov.au'
                    ]
                }]
            })).validate_case_studies()) == 1


@pytest.mark.parametrize('recruiter', ['no', 'both'])
def test_can_get_errors_as_non_recruiter_with_no_case_studies(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                }
            })).validate_case_studies()) == 1


def test_for_no_errors_as_recruiter_with_no_case_studies():
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': 'yes',
                'services': {
                    'service_1': True
                }
            })).validate_case_studies()) == 0


@pytest.mark.parametrize('recruiter', ['no', 'both'])
def test_can_succeed_as_non_recruiter_with_filled_fields(recruiter):
    assert len(ApplicationValidator(
        Application(
            data={
                'recruiter': recruiter,
                'services': {
                    'service_1': True
                },
                'case_studies': [{
                    'title': '1',
                    'client': '2',
                    'timeframe': '3',
                    'roles': '4',
                    'opportunity': '5',
                    'approach': '6',
                    'referee_name': '7',
                    'referee_position': '8',
                    'referee_contact': '9',
                    'referee_email': '10',
                    'outcome': [
                        '11'
                    ],
                    'project_links': [
                        'http://dta.gov.au'
                    ],
                    'service': 'service_1'
                }]
            })).validate_case_studies()) == 0
