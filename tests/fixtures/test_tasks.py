from datetime import date, timedelta
from os import environ

import pytest
from flask import current_app
from mock.mock import MagicMock
from requests.exceptions import RequestException

from app import db
from app.api.services import AuditTypes as audit_types
from app.models import (Application, Assessment, AuditEvent, Supplier,
                        SupplierDomain)
from app.tasks.jira import (sync_application_approvals_with_jira,
                            sync_domain_assessment_approvals_with_jira)
from app.tasks.mailchimp import (MailChimpConfigException,
                                 send_document_expiry_campaign,
                                 send_document_expiry_reminder,
                                 send_new_briefs_email,
                                 sync_mailchimp_seller_list)
from app.tasks.s3 import CreateResponsesZipException, create_responses_zip
from dmapiclient.audit import AuditTypes
from tests.app.helpers import (COMPLETE_DIGITAL_SPECIALISTS_BRIEF,
                               INCOMING_APPLICATION_DATA)

briefs_data_all_sellers = COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy()
briefs_data_all_sellers.update({'sellerSelector': 'allSellers'})


@pytest.mark.parametrize('suppliers', [{'framework_slug': 'digital-marketplace'}], indirect=True)
@pytest.mark.parametrize(
    'users',
    [{'framework_slug': 'digital-marketplace', 'user_role': 'supplier', 'email_domain': 'supplier.com'}],
    indirect=True
)
def test_sync_mailchimp_seller_list_success(app, mocker, suppliers, supplier_domains, users):
    mailchimp = mocker.patch('app.tasks.mailchimp.MailChimp')
    client = MagicMock()

    list_response = {
        'members': [
            {'email_address': 'test1@test.com'},
            {'email_address': 'test2@test.com'}
        ]
    }
    supplier_emails = [x.data['contact_email'].lower() for x in suppliers]
    user_emails = [x.email_address.lower() for x in users]
    emails_to_subscribe = supplier_emails + user_emails

    mailchimp.return_value = client

    with app.app_context():
        environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

        client.lists.members.all.return_value = list_response

        sync_mailchimp_seller_list()

        client.lists.members.all.assert_called_with('123456', fields='members.email_address,members.id', get_all=True)
        client.lists.update_members.assert_any_call(list_id='123456', data={
            'members': [{
                'email_address': email,
                'status': 'subscribed'
            } for email in emails_to_subscribe]
        })


def test_sync_mailchimp_seller_list_fails_mailchimp_api_call_with_requests_error(app, mocker):
    mailchimp = mocker.patch('app.tasks.mailchimp.MailChimp')
    requestEx = mocker.patch('app.tasks.mailchimp.RequestException')
    client = MagicMock()

    mailchimp.return_value = client

    with app.app_context():
        environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'
        client.lists.members.all.side_effect = RequestException

        try:
            sync_mailchimp_seller_list()
            assert False
        except RequestException as e:
            assert True


def test_sync_mailchimp_seller_list_fails_with_empty_list_id(app, mocker):
    mailchimp = mocker.patch('app.tasks.mailchimp.MailChimp')
    client = MagicMock()

    mailchimp.return_value = client

    with app.app_context():
        environ['MAILCHIMP_SELLER_LIST_ID'] = ''

        try:
            sync_mailchimp_seller_list()
            assert False
        except MailChimpConfigException as e:
            assert str(e) == 'Failed to get MAILCHIMP_SELLER_LIST_ID from the environment variables.'


@pytest.mark.parametrize('briefs', [{'data': briefs_data_all_sellers}], indirect=True)
def test_send_new_briefs_email_success(app, briefs, mocker):
    mailchimp = mocker.patch('app.tasks.mailchimp.MailChimp')
    client = MagicMock()

    mailchimp.return_value = client
    environ['MAILCHIMP_SELLER_EMAIL_LIST_ID'] = '123456'

    with app.app_context():
        send_new_briefs_email()

        assert client.campaigns.create.called
        assert client.campaigns.content.update.called
        assert client.campaigns.actions.schedule.called

        audit_event = AuditEvent.query.filter(
            AuditEvent.type == AuditTypes.send_seller_opportunities_campaign.value
        ).first()

        assert audit_event
        assert audit_event.data['briefs_sent'] == len(briefs)


@pytest.mark.parametrize(
    'briefs',
    [{'published_at': '%s-01-01' % (date.today().year - 1), 'data': briefs_data_all_sellers}],
    indirect=True
)
def test_send_new_briefs_email_fails_no_new_briefs_in_past_24hrs(app, briefs, mocker):
    mailchimp = mocker.patch('app.tasks.mailchimp.MailChimp')
    client = MagicMock()

    mailchimp.return_value = client
    environ['MAILCHIMP_SELLER_EMAIL_LIST_ID'] = '123456'

    with app.app_context():
        send_new_briefs_email()

        assert not client.campaigns.create.called
        assert not client.campaigns.content.update.called
        assert not client.campaigns.actions.schedule.called


def test_send_new_briefs_email_fails_no_new_briefs_since_last_run(app, briefs, mocker):
    mailchimp = mocker.patch('app.tasks.mailchimp.MailChimp')
    client = MagicMock()

    mailchimp.return_value = client
    environ['MAILCHIMP_SELLER_EMAIL_LIST_ID'] = '123456'

    with app.app_context():

        audit = AuditEvent(
            audit_type=AuditTypes.send_seller_opportunities_campaign,
            user=None,
            data={},
            db_object=None
        )
        db.session.add(audit)
        db.session.commit()

        send_new_briefs_email()

        assert not client.campaigns.create.called
        assert not client.campaigns.content.update.called
        assert not client.campaigns.actions.schedule.called


def test_send_new_briefs_email_fails_with_empty_list_id(app, mocker):
    mailchimp = mocker.patch('app.tasks.mailchimp.MailChimp')
    client = MagicMock()

    mailchimp.return_value = client
    environ['MAILCHIMP_SELLER_EMAIL_LIST_ID'] = ''

    with app.app_context():
        try:
            send_new_briefs_email()
            assert False
        except MailChimpConfigException as e:
            assert str(e) == 'Failed to get MAILCHIMP_SELLER_EMAIL_LIST_ID from the environment variables.'


@pytest.mark.parametrize('briefs', [{'data': briefs_data_all_sellers}], indirect=True)
def test_send_new_briefs_email_fails_mailchimp_api_call_with_requests_error(app, briefs, mocker):
    mailchimp = mocker.patch('app.tasks.mailchimp.MailChimp')
    requestEx = mocker.patch('app.tasks.mailchimp.RequestException')
    client = MagicMock()

    mailchimp.return_value = client
    environ['MAILCHIMP_SELLER_EMAIL_LIST_ID'] = '123456'

    client.campaigns.create.side_effect = RequestException

    with app.app_context():
        try:
            send_new_briefs_email()
            assert False
        except RequestException as e:
            assert True


brief_response_data = {
    'attachedDocumentURL': [
        'attachment_1.pdf',
        'attachment_2.pdf'
    ]
}


@pytest.mark.parametrize('brief_responses', [{'data': brief_response_data}], indirect=True)
def test_create_responses_zip_success(app, briefs, brief_responses, mocker):
    boto3 = mocker.patch('app.tasks.s3.boto3')
    s3 = MagicMock()
    bucket = MagicMock()

    boto3.resource.return_value = s3
    s3.Bucket.return_value = bucket

    with app.app_context():
        create_responses_zip(1)
        assert boto3.resource.called
        assert s3.Bucket.called
        assert bucket.download_fileobj.called
        assert bucket.upload_fileobj.called


brief_response_data = {
    'attachedDocumentURL': []
}


def test_create_responses_zip_fails_when_no_responses(app, briefs, mocker):
    boto3 = mocker.patch('app.tasks.s3.boto3')
    s3 = MagicMock()
    bucket = MagicMock()

    boto3.resource.return_value = s3
    s3.Bucket.return_value = bucket

    with app.app_context():
        try:
            create_responses_zip(1)
            assert False
        except CreateResponsesZipException as e:
            assert not boto3.resource.called
            assert not s3.Bucket.called
            assert not bucket.download_fileobj.called
            assert not bucket.upload_fileobj.called
            assert str(e) == 'There were no respones for brief id 1'


@pytest.fixture
def mock_jira_application_response(mocker):
    marketplace_jira = MagicMock()

    marketplace_jira.find_approved_application_issues.return_value = {
        'issues': [{
            'fields': {
                current_app.config['JIRA_FIELD_CODES'].get('APPLICATION_FIELD_CODE'): '1'
            },
            'key': 'MARADMIN-123'
        }]
    }
    get_marketplace_jira = mocker.patch('app.tasks.jira.get_marketplace_jira', autospec=True)
    get_marketplace_jira.return_value = marketplace_jira
    yield get_marketplace_jira


@pytest.fixture
def application(app, applications):
    with app.app_context():
        application = db.session.query(Application).filter(Application.id == 1).first()
        application.data = INCOMING_APPLICATION_DATA
        application.status = 'submitted'
        yield application


def test_sync_jira_application_approvals_task_updates_applications(app, application, mocker,
                                                                   mock_jira_application_response):
    with app.app_context():
        approval_notification = mocker.patch('app.tasks.jira.send_approval_notification', autospec=True)

        sync_application_approvals_with_jira()

        updated_application = db.session.query(Application).filter(Application.id == 1).first()
        assert updated_application.status == 'approved'
        assert approval_notification.called


def test_sync_jira_application_approvals_task_creates_audit_event_on_approval(app, application,
                                                                              mock_jira_application_response):
    with app.app_context():
        sync_application_approvals_with_jira()

        audit_event = (db.session.query(AuditEvent).filter(
            AuditEvent.type == AuditTypes.approve_application.value,
            AuditEvent.object_id == application.id).first())

        assert audit_event.data['jira_issue_key'] == 'MARADMIN-123'


@pytest.fixture
def mock_jira_assessment_response(mocker):
    marketplace_jira = MagicMock()
    marketplace_jira.find_approved_assessment_issues.return_value = {
        'issues': [{
            'fields': {
                current_app.config['JIRA_FIELD_CODES'].get('SUPPLIER_FIELD_CODE'): '123',
                'labels': ['Strategy_And_Policy']
            },
            'key': 'MARADMIN-123'
        }]
    }
    get_marketplace_jira = mocker.patch('app.tasks.jira.get_marketplace_jira', autospec=True)
    get_marketplace_jira.return_value = marketplace_jira

    yield get_marketplace_jira


@pytest.fixture
def expiry_date():
    expiry_date = date.today() + timedelta(days=28)
    yield expiry_date.isoformat()


@pytest.fixture
def supplier(app, expiry_date):
    with app.app_context():
        db.session.add(Supplier(id=1, code=123, name='ABC', data={
            'contact_email': 'business.contact@digital.gov.au',
            'email': 'authorised.rep@digital.gov.au',
            'documents': {
                'liability': {
                    'expiry': expiry_date
                }
            }
        }))
        yield db.session.query(Supplier).filter(Supplier.id == 1).first()


@pytest.fixture
def supplier_domain(app, domains, supplier):
    with app.app_context():
        db.session.add(SupplierDomain(id=1, domain_id=1, status='unassessed', supplier_id=1))
        yield db.session.query(SupplierDomain).filter(SupplierDomain.id == 1).first()


@pytest.fixture
def assessment(app, supplier_domain):
    with app.app_context():
        db.session.add(Assessment(id=1, supplier_domain_id=1))
        yield db.session.query(Assessment).filter(Assessment.id == 1).first()


def test_sync_jira_domain_assessment_approvals_task_updates_supplier_domain(app, assessment, mocker,
                                                                            mock_jira_assessment_response):
    with app.app_context():
        approval_notification = mocker.patch('app.tasks.jira.send_assessment_approval_notification', autospec=True)

        sync_domain_assessment_approvals_with_jira()

        supplier_domain = db.session.query(SupplierDomain).filter(SupplierDomain.id == 1).first()
        assert supplier_domain.status == 'assessed'
        assert approval_notification.called


def test_sync_jira_domain_assessment_approvals_task_creates_audit_event_on_approval(app, assessment,
                                                                                    mock_jira_assessment_response):
    with app.app_context():
        sync_domain_assessment_approvals_with_jira()

        audit_event = (db.session.query(AuditEvent).filter(
            AuditEvent.type == AuditTypes.assessed_domain.value,
            AuditEvent.object_id == assessment.id).first())

        assert audit_event.data['jira_issue_key'] == 'MARADMIN-123'


@pytest.fixture
def audit_events(app, suppliers_service):
    with app.app_context():
        db.session.add(AuditEvent(
            audit_type=audit_types.sent_expiring_documents_email,
            data={
                'campaign_title': ('Expiring documents - {}'
                                   .format(date.today().isoformat())),
                'sellers': suppliers_service.get_suppliers_with_expiring_documents()
            },
            db_object=None,
            user=None
        ))
        yield db.session.query(AuditEvent).all()


@pytest.fixture
def suppliers_service(expiry_date, mocker, supplier):
    suppliers = mocker.patch('app.tasks.mailchimp.suppliers')
    suppliers.get_suppliers_with_expiring_documents.return_value = [
        {
            'code': 123,
            'documents': [
                {
                    'expiry': expiry_date,
                    'type': 'liability'
                }
            ],
            'email_addresses': [
                'authorised.rep@digital.gov.au',
                'business.contact@digital.gov.au',
                'abc.user@digital.gov.au'
            ],
            'name': 'ABC'
        }
    ]

    suppliers.get_supplier_by_code.return_value = supplier
    yield suppliers


def test_document_expiry_campaign_is_not_created_when_no_sellers_with_expiring_documents(mocker,
                                                                                         suppliers_service):
    mailchimp = mocker.patch('app.tasks.mailchimp.MailChimp')
    client = MagicMock()
    mailchimp.return_value = client

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    suppliers_service.get_suppliers_with_expiring_documents.return_value = []

    send_document_expiry_reminder()

    assert not client.campaigns.create.called
    assert not client.campaigns.content.update.called
    assert not client.campaigns.actions.schedule.called


def test_document_expiry_campaign_is_not_created_if_audit_event_exists(audit_events, mocker,
                                                                       supplier, suppliers_service):
    mailchimp = mocker.patch('app.tasks.mailchimp.MailChimp')
    client = MagicMock()
    mailchimp.return_value = client

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    send_document_expiry_reminder()

    assert not client.campaigns.create.called
    assert not client.campaigns.content.update.called
    assert not client.campaigns.actions.schedule.called


def test_document_expiry_campaign_success(mocker, supplier, suppliers_service):
    mailchimp = mocker.patch('app.tasks.mailchimp.MailChimp')
    client = MagicMock()
    mailchimp.return_value = client

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    client.campaigns.create.return_value = {
        'id': 123
    }

    send_document_expiry_reminder()

    assert client.campaigns.create.called
    assert client.campaigns.content.update.called
    assert client.campaigns.actions.schedule.called


def test_document_expiry_campaign_is_created_with_segment_options(mocker, supplier, suppliers_service):
    mailchimp = mocker.patch('app.tasks.mailchimp.MailChimp')
    client = MagicMock()
    mailchimp.return_value = client

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    client.campaigns.create.return_value = {
        'id': 123
    }

    email_addresses = suppliers_service.get_suppliers_with_expiring_documents()[0]['email_addresses']
    sellers = suppliers_service.get_suppliers_with_expiring_documents()

    send_document_expiry_campaign(client, sellers)

    segment_options = client.campaigns.create.call_args[1]['data']['recipients']['segment_opts']

    assert segment_options['match'] == 'any'
    assert len(segment_options['conditions']) == 3
    for condition in segment_options['conditions']:
        assert condition['condition_type'] == 'EmailAddress'
        assert condition['op'] == 'is'
        assert condition['field'] == 'EMAIL'
        assert condition['value'] in email_addresses


def test_document_expiry_campaign_adds_audit_event_on_success(expiry_date, mocker, supplier, suppliers_service):
    mailchimp = mocker.patch('app.tasks.mailchimp.MailChimp')
    client = MagicMock()
    mailchimp.return_value = client

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    client.campaigns.create.return_value = {
        'id': 123
    }

    assert db.session.query(AuditEvent).count() == 0

    sellers = suppliers_service.get_suppliers_with_expiring_documents()
    send_document_expiry_campaign(client, sellers)

    audit_event = db.session.query(AuditEvent).first()
    assert audit_event.type == audit_types.sent_expiring_documents_email.value
    assert audit_event.data['campaign_title'] == ('Expiring documents - {}'
                                                  .format(date.today().isoformat()))
    assert audit_event.data['sellers'] == suppliers_service.get_suppliers_with_expiring_documents()
