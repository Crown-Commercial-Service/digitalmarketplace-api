from app.api.business.validators import EvidenceDataValidator
import json
import mock
import pytest


evidence_data = {
    'domainId': 1,
    'maxDailyRate': 1000,
    'criteria': [1, 2],
    'evidence': {
        '1': {
            'startDate': '2018',
            'endDate': '2019',
            'client': 'X Client',
            'refereeName': 'ddd',
            'refereeNumber': '123456789',
            'background': 'This and that',
            'response': 'aaa'
        },
        '2': {
            'startDate': '2018',
            'endDate': '2018',
            'client': 'X Client',
            'refereeName': 'ddd',
            'refereeNumber': '123456789',
            'background': 'This and that',
            'response': 'bbb'
        }
    }
}


@mock.patch('app.tasks.publish_tasks.evidence')
def test_evidence_creation_success(publish_task, client, supplier_user):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/evidence/1', content_type='application/json')
    assert res.status_code == 200

    response = json.loads(res.data)
    assert response['id'] == 1

    res = client.get('/2/evidence/1', content_type='application/json')
    assert res.status_code == 200


def test_evidence_creation_failed_invalid_brief(client, supplier_user, rfx_brief):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/evidence/1/12222', content_type='application/json')
    assert res.status_code == 400


@mock.patch('app.tasks.publish_tasks.evidence')
def test_evidence_creation_fail_already_in_draft(publish_task, client, supplier_user):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/evidence/1', content_type='application/json')
    assert res.status_code == 200

    response = json.loads(res.data)
    assert response['id'] == 1

    data = evidence_data
    res = client.patch('/2/evidence/1', content_type='application/json', data=json.dumps(evidence_data))
    response = json.loads(res.data)
    assert res.status_code == 200
    assert not response['submitted_at']

    res = client.post('/2/evidence/1', content_type='application/json')
    assert res.status_code == 400


@mock.patch('app.tasks.publish_tasks.evidence')
@mock.patch('app.api.views.evidence.create_evidence_assessment_in_jira')
def test_evidence_creation_fail_already_submitted(publish_task, jira_task, client, supplier_user):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/evidence/1', content_type='application/json')
    assert res.status_code == 200

    response = json.loads(res.data)
    assert response['id'] == 1

    data = evidence_data
    data['publish'] = True
    res = client.patch('/2/evidence/1', content_type='application/json', data=json.dumps(evidence_data))
    response = json.loads(res.data)
    assert res.status_code == 200
    assert response['submitted_at']

    res = client.post('/2/evidence/1', content_type='application/json')
    assert res.status_code == 400


@mock.patch('app.tasks.publish_tasks.evidence')
@mock.patch('app.api.views.evidence.create_evidence_assessment_in_jira')
@pytest.mark.parametrize(
    'supplier_domains',
    [{'status': 'assessed'}],
    indirect=True
)
def test_evidence_creation_fail_already_assessed(publish_task, jira_task, client, supplier_user, supplier_domains):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/evidence/1', content_type='application/json')
    assert res.status_code == 400


def test_evidence_validate_max_rate(domains):
    data = {
        'maxDailyRate': 100
    }
    valid = EvidenceDataValidator(data).validate_max_rate()
    assert valid

    data = {}
    valid = EvidenceDataValidator(data).validate_max_rate()
    assert not valid

    data = {
        'maxDailyRate': 0
    }
    valid = EvidenceDataValidator(data).validate_max_rate()
    assert not valid

    data = {
        'maxDailyRate': -1
    }
    valid = EvidenceDataValidator(data).validate_max_rate()
    assert not valid

    data = {
        'maxDailyRate': ''
    }
    valid = EvidenceDataValidator(data).validate_max_rate()
    assert not valid

    data = {
        'maxDailyRate': 'abc'
    }
    valid = EvidenceDataValidator(data).validate_max_rate()
    assert not valid


def test_evidence_validate_domain(domains, evidence):
    data = {}
    valid = EvidenceDataValidator(data, evidence[0]).validate_domain()
    assert valid

    valid = EvidenceDataValidator(data).validate_domain()
    assert not valid


def test_evidence_validate_criteria(domains, evidence):
    ev = next(x for x in evidence if x.domain.id == 1)
    data = {
        'criteria': [1, 2]
    }
    valid = EvidenceDataValidator(data, ev).validate_criteria()
    assert valid

    data = {
        'criteria': [1, 2],
        'maxDailyRate': 5
    }
    valid = EvidenceDataValidator(data, ev).validate_criteria()
    assert valid

    data = {
        'criteria': [1, 2, 3],
        'maxDailyRate': 55555
    }
    valid = EvidenceDataValidator(data, ev).validate_criteria()
    assert valid

    data = {}
    valid = EvidenceDataValidator(data, ev).validate_criteria()
    assert not valid

    data = {
        'criteria': []
    }
    valid = EvidenceDataValidator(data, ev).validate_criteria()
    assert not valid

    data = {
        'criteria': [11, 22]
    }
    valid = EvidenceDataValidator(data, ev).validate_criteria()
    assert not valid

    data = {
        'criteria': [1, 2],
        'maxDailyRate': 55555
    }
    valid = EvidenceDataValidator(data, ev).validate_criteria()
    assert not valid


def test_evidence_validate_evidence_response(domains, evidence):
    ev = next(x for x in evidence if x.domain.id == 1)
    data = {
        'criteria': [1, 2],
        'evidence': {
            '1': {
                'response': 'aaaa'
            },
            '2': {
                'response': 'bbbb'
            }
        }
    }
    valid = EvidenceDataValidator(data, ev).validate_evidence_responses()
    assert valid

    data = {
        'criteria': [1, 2],
        'maxDailyRate': 5,
        'evidence': {
            '1': {
                'response': 'aaaa'
            },
            '2': {
                'response': 'bbbb'
            }
        }
    }
    valid = EvidenceDataValidator(data, ev).validate_evidence_responses()
    assert valid

    data = {
        'criteria': [1, 2, 3],
        'maxDailyRate': 55555,
        'evidence': {
            '1': {
                'response': 'aaaa'
            },
            '2': {
                'response': 'bbbb'
            },
            '3': {
                'response': 'cccc'
            }
        }
    }
    valid = EvidenceDataValidator(data, ev).validate_evidence_responses()
    assert valid

    data = {}
    valid = EvidenceDataValidator(data, ev).validate_evidence_responses()
    assert not valid

    data = {
        'evidence': {}
    }
    valid = EvidenceDataValidator(data, ev).validate_evidence_responses()
    assert not valid

    data = {
        'criteria': [1, 2],
        'evidence': {
            '1': {
                'response': 'aaaa'
            }
        }
    }
    valid = EvidenceDataValidator(data, ev).validate_evidence_responses()
    assert not valid

    data = {
        'criteria': [1, 2],
        'evidence': {
            '1': {
                'response': 'aaaa'
            },
            '2': {
                'response': ''
            }
        }
    }
    valid = EvidenceDataValidator(data, ev).validate_evidence_responses()
    assert not valid

    data = {
        'criteria': [1, 2],
        'maxDailyRate': 55555,
        'evidence': {
            '1': {
                'response': 'aaaa'
            },
            '2': {
                'response': 'bbbb'
            }
        }
    }
    valid = EvidenceDataValidator(data, ev).validate_evidence_responses()
    assert not valid


def test_all_essential_criteria_have_been_selected(domains, evidence):
    platform_category = (
        next(domain for domain in domains if domain.name == 'Platforms integration')
    )

    ev = next(x for x in evidence if x.domain.id == platform_category.id)

    data = {
        'criteria': [85, 86]
    }

    valid = EvidenceDataValidator(data, ev).validate_selected_essential_criteria()
    assert valid


def test_some_essential_criteria_have_been_selected(domains, evidence):
    platform_category = (
        next(domain for domain in domains if domain.name == 'Platforms integration')
    )

    ev = next(x for x in evidence if x.domain.id == platform_category.id)

    data = {
        'criteria': [86]
    }

    valid = EvidenceDataValidator(data, ev).validate_selected_essential_criteria()
    assert not valid


def test_all_essential_criteria_have_responses(domains, evidence):
    platform_category = (
        next(domain for domain in domains if domain.name == 'Platforms integration')
    )

    ev = next(x for x in evidence if x.domain.id == platform_category.id)

    data = {
        'criteria': [85, 86],
        'evidence': {
            '85': {
                'response': 'aaaa'
            },
            '86': {
                'response': 'bbbb'
            }
        }
    }

    valid = EvidenceDataValidator(data, ev).validate_essential_criteria_responses()
    assert valid


def test_some_essential_criteria_have_responses(domains, evidence):
    platform_category = (
        next(domain for domain in domains if domain.name == 'Platforms integration')
    )

    ev = next(x for x in evidence if x.domain.id == platform_category.id)

    data = {
        'criteria': [85, 86],
        'evidence': {
            '86': {
                'response': 'bbbb'
            }
        }
    }

    valid = EvidenceDataValidator(data, ev).validate_essential_criteria_responses()
    assert not valid
