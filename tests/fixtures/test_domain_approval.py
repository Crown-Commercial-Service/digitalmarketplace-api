from app.api.business.domain_approval import DomainApproval, DomainApprovalException
import pytest
import mock


evidence_data = {
    'domainId': 1,
    'maxDailyRate': 1000,
    'criteria': [1, 2],
    'evidence': {
        '1': {
            'endDate': '2019',
            'client': 'X Client',
            'background': 'This and that',
            'response': 'aaa'
        },
        '2': {
            'endDate': '2018',
            'client': 'X Client',
            'background': 'This and that',
            'response': 'bbb'
        }
    }
}


@mock.patch('app.tasks.publish_tasks.evidence')
@pytest.mark.parametrize('evidence', [
    {
        'data': evidence_data
    }
], indirect=True)
def test_domain_approval_approve_success(publish_task, domains, evidence, suppliers, admin_users):
    admin_user_id = admin_users[0].id
    for e in evidence:
        domain_approval = DomainApproval(
            evidence_id=e.id,
            actioned_by=admin_user_id
        )

        supplier = suppliers[0]
        assert e.domain.name not in supplier.assessed_domains
        assert e.status == 'submitted'

        domain_approval.approve_domain()

        assert e.domain.name in supplier.assessed_domains
        assert e.status == 'assessed'


@mock.patch('app.tasks.publish_tasks.evidence')
@pytest.mark.parametrize('evidence', [
    {
        'data': evidence_data
    }
], indirect=True)
def test_domain_approval_reject_success(publish_task, domains, evidence, suppliers, admin_users):
    admin_user_id = admin_users[0].id
    for e in evidence:
        domain_approval = DomainApproval(
            evidence_id=e.id,
            actioned_by=admin_user_id
        )

        supplier = suppliers[0]
        assert e.domain.name not in supplier.assessed_domains
        assert e.status == 'submitted'

        domain_approval.reject_domain({}, False)

        assert e.domain.name not in supplier.assessed_domains
        assert e.status == 'rejected'
