from datetime import date, timedelta
from os import environ

import pytest
import mock
from flask import current_app
from mock.mock import MagicMock
from requests.exceptions import RequestException

from app import db
from app.api.services import AuditTypes as audit_types
from app.models import (Application, Assessment, AuditEvent, Supplier,
                        SupplierDomain)
from app.tasks.mailchimp import (MailChimpConfigException,
                                 send_document_expiry_campaign,
                                 send_document_expiry_reminder,
                                 send_labour_hire_expiry_reminder,
                                 send_labour_hire_licence_expiry_campaign,
                                 send_new_briefs_email,
                                 sync_mailchimp_seller_list)
from app.tasks.s3 import CreateResponsesZipException, create_responses_zip
from dmapiclient.audit import AuditTypes
from tests.app.helpers import (COMPLETE_DIGITAL_SPECIALISTS_BRIEF,
                               INCOMING_APPLICATION_DATA)

briefs_data_all_sellers = COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy()
briefs_data_all_sellers.update({'sellerSelector': 'allSellers'})


@mock.patch('app.tasks.mailchimp.MailChimp')
@pytest.mark.parametrize('suppliers', [{'framework_slug': 'digital-marketplace'}], indirect=True)
@pytest.mark.parametrize(
    'users',
    [{'framework_slug': 'digital-marketplace', 'user_role': 'supplier', 'email_domain': 'supplier.com'}],
    indirect=True
)
def test_sync_mailchimp_seller_list_success(mock_mailchimp, app, suppliers, supplier_domains, users):
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

    mock_mailchimp.return_value = client

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


@mock.patch('app.tasks.mailchimp.RequestException')
@mock.patch('app.tasks.mailchimp.MailChimp')
def test_sync_mailchimp_seller_list_fails_mailchimp_api_call_with_requests_error(mock_mailchimp, mock_request_exception,
                                                                                 app):
    client = MagicMock()
    mock_mailchimp.return_value = client

    with app.app_context():
        environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'
        client.lists.members.all.side_effect = RequestException

        try:
            sync_mailchimp_seller_list()
            assert False
        except RequestException as e:
            assert True


@mock.patch('app.tasks.mailchimp.MailChimp')
def test_sync_mailchimp_seller_list_fails_with_empty_list_id(mock_mailchimp, app):
    client = MagicMock()
    mock_mailchimp.return_value = client

    with app.app_context():
        environ['MAILCHIMP_SELLER_LIST_ID'] = ''

        try:
            sync_mailchimp_seller_list()
            assert False
        except MailChimpConfigException as e:
            assert str(e) == 'Failed to get MAILCHIMP_SELLER_LIST_ID from the environment variables.'


@mock.patch('app.tasks.mailchimp.MailChimp')
@pytest.mark.parametrize('briefs', [
    {
        'data': briefs_data_all_sellers,
        'framework_slug': 'digital-marketplace'
    }
], indirect=True)
def test_send_new_briefs_email_success(mock_mailchimp, app, briefs):
    client = MagicMock()
    mock_mailchimp.return_value = client
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


@mock.patch('app.tasks.mailchimp.MailChimp')
@pytest.mark.parametrize(
    'briefs',
    [{'published_at': '%s-01-01' % (date.today().year - 1), 'data': briefs_data_all_sellers}],
    indirect=True
)
def test_send_new_briefs_email_fails_no_new_briefs_in_past_24hrs(mock_mailchimp, app, briefs):
    client = MagicMock()
    mock_mailchimp.return_value = client
    environ['MAILCHIMP_SELLER_EMAIL_LIST_ID'] = '123456'

    with app.app_context():
        send_new_briefs_email()

        assert not client.campaigns.create.called
        assert not client.campaigns.content.update.called
        assert not client.campaigns.actions.schedule.called


@mock.patch('app.tasks.mailchimp.MailChimp')
def test_send_new_briefs_email_fails_no_new_briefs_since_last_run(mock_mailchimp, app, briefs):
    client = MagicMock()
    mock_mailchimp.return_value = client
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


@mock.patch('app.tasks.mailchimp.MailChimp')
def test_send_new_briefs_email_fails_with_empty_list_id(mock_mailchimp, app):
    client = MagicMock()
    mock_mailchimp.return_value = client
    environ['MAILCHIMP_SELLER_EMAIL_LIST_ID'] = ''

    with app.app_context():
        try:
            send_new_briefs_email()
            assert False
        except MailChimpConfigException as e:
            assert str(e) == 'Failed to get MAILCHIMP_SELLER_EMAIL_LIST_ID from the environment variables.'


@mock.patch('app.tasks.mailchimp.Exception')
@mock.patch('app.tasks.mailchimp.RequestException')
@mock.patch('app.tasks.mailchimp.MailChimp')
@pytest.mark.parametrize('briefs', [
    {
        'data': briefs_data_all_sellers,
        'framework_slug': 'digital-marketplace'
    }
], indirect=True)
def test_send_new_briefs_email_fails_mailchimp_api_call_with_requests_error(mock_mailchimp, mock_request_exception,
                                                                            mock_exception, app, briefs):
    client = MagicMock()
    mock_mailchimp.return_value = client
    environ['MAILCHIMP_SELLER_EMAIL_LIST_ID'] = '123456'

    client.campaigns.create.side_effect = RequestException

    with app.app_context():
        try:
            send_new_briefs_email()
            assert False
        except RequestException as e:
            assert True
        except mock_exception as error:
            assert False


brief_response_data = {
    'attachedDocumentURL': [
        'attachment_1.pdf',
        'attachment_2.pdf'
    ]
}


@mock.patch('app.tasks.s3.boto3')
@pytest.mark.parametrize('brief_responses', [{'data': brief_response_data}], indirect=True)
def test_create_responses_zip_success(mock_boto3, app, briefs, brief_responses):
    s3 = MagicMock()
    bucket = MagicMock()

    mock_boto3.resource.return_value = s3
    s3.Bucket.return_value = bucket

    with app.app_context():
        create_responses_zip(1)
        assert mock_boto3.resource.called
        assert s3.Bucket.called
        assert bucket.download_fileobj.called
        assert bucket.upload_fileobj.called


brief_response_data = {
    'attachedDocumentURL': []
}


@mock.patch('app.tasks.s3.boto3')
def test_create_responses_zip_fails_when_no_responses(mock_boto3, app, briefs):
    s3 = MagicMock()
    bucket = MagicMock()

    mock_boto3.resource.return_value = s3
    s3.Bucket.return_value = bucket

    with app.app_context():
        try:
            create_responses_zip(1)
            assert False
        except CreateResponsesZipException as e:
            assert not mock_boto3.resource.called
            assert not s3.Bucket.called
            assert not bucket.download_fileobj.called
            assert not bucket.upload_fileobj.called
            assert str(e) == 'There were no responses for opportunity id 1'


@pytest.fixture
def application(app, applications):
    with app.app_context():
        application = db.session.query(Application).filter(Application.id == 1).first()
        application.data = INCOMING_APPLICATION_DATA
        application.status = 'submitted'
        yield application


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


@pytest.fixture
def audit_events(app, suppliers_with_expiring_documents, suppliers_with_expiring_labour_hire_licences):
    with app.app_context():
        db.session.add(AuditEvent(
            audit_type=audit_types.sent_expiring_documents_email,
            data={
                'campaign_title': ('Expiring documents - {}'
                                   .format(date.today().isoformat())),
                'sellers': suppliers_with_expiring_documents
            },
            db_object=None,
            user=None
        ))
        db.session.add(AuditEvent(
            audit_type=audit_types.sent_expiring_licence_email,
            data={
                'campaign_title': ('Expiring labour hire licence - {}'
                                   .format(date.today().isoformat())),
                'sellers': suppliers_with_expiring_labour_hire_licences
            },
            db_object=None,
            user=None
        ))
        yield db.session.query(AuditEvent).all()


@pytest.fixture
def suppliers_with_expiring_documents(expiry_date):
    suppliers = [
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

    yield suppliers


@pytest.fixture
def suppliers_with_expiring_labour_hire_licences(expiry_date):
    suppliers = [
        {
            'code': 123,
            'labourHire': [
                {
                    'state': 'vic',
                    'expiry': expiry_date,
                    'licenceNumber': '123456'
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

    yield suppliers


@mock.patch('app.tasks.mailchimp.suppliers.get_supplier_by_code')
@mock.patch('app.tasks.mailchimp.suppliers.get_suppliers_with_expiring_documents')
@mock.patch('app.tasks.mailchimp.MailChimp')
def test_document_expiry_campaign_is_not_created_when_no_sellers_with_expiring_documents(
    mock_mailchimp,
    mock_get_suppliers_with_expiring_documents,
    mock_get_supplier_by_code,
    supplier
):
    client = MagicMock()
    mock_mailchimp.return_value = client
    mock_get_suppliers_with_expiring_documents.return_value = []
    mock_get_supplier_by_code.return_value = supplier

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    send_document_expiry_reminder()

    assert not client.campaigns.create.called
    assert not client.campaigns.content.update.called
    assert not client.campaigns.actions.schedule.called


@mock.patch('app.tasks.mailchimp.suppliers.get_supplier_by_code')
@mock.patch('app.tasks.mailchimp.suppliers.get_suppliers_with_expiring_documents')
@mock.patch('app.tasks.mailchimp.MailChimp')
def test_document_expiry_campaign_is_not_created_if_audit_event_exists(
    mock_mailchimp,
    mock_get_suppliers_with_expiring_documents,
    mock_get_supplier_by_code,
    audit_events,
    supplier,
    suppliers_with_expiring_documents
):
    client = MagicMock()
    mock_mailchimp.return_value = client
    mock_get_suppliers_with_expiring_documents.return_value = suppliers_with_expiring_documents
    mock_get_supplier_by_code.return_value = supplier

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    send_document_expiry_reminder()

    assert not client.campaigns.create.called
    assert not client.campaigns.content.update.called
    assert not client.campaigns.actions.schedule.called


@mock.patch('app.tasks.mailchimp.suppliers.get_supplier_by_code')
@mock.patch('app.tasks.mailchimp.suppliers.get_suppliers_with_expiring_documents')
@mock.patch('app.tasks.mailchimp.MailChimp')
def test_document_expiry_campaign_success(
    mock_mailchimp,
    mock_get_suppliers_with_expiring_documents,
    mock_get_supplier_by_code,
    supplier,
    suppliers_with_expiring_documents
):
    client = MagicMock()
    mock_mailchimp.return_value = client
    mock_get_suppliers_with_expiring_documents.return_value = suppliers_with_expiring_documents
    mock_get_supplier_by_code.return_value = supplier

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    client.campaigns.create.return_value = {
        'id': 123
    }

    send_document_expiry_reminder()

    assert client.campaigns.create.called
    assert client.campaigns.content.update.called
    assert client.campaigns.actions.schedule.called


@mock.patch('app.tasks.mailchimp.suppliers.get_supplier_by_code')
@mock.patch('app.tasks.mailchimp.suppliers.get_suppliers_with_expiring_documents')
@mock.patch('app.tasks.mailchimp.MailChimp')
def test_document_expiry_campaign_is_created_with_segment_options(
    mock_mailchimp,
    mock_get_suppliers_with_expiring_documents,
    mock_get_supplier_by_code,
    supplier,
    suppliers_with_expiring_documents
):
    client = MagicMock()
    mock_mailchimp.return_value = client
    mock_get_suppliers_with_expiring_documents.return_value = suppliers_with_expiring_documents
    mock_get_supplier_by_code.return_value = supplier

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    client.campaigns.create.return_value = {
        'id': 123
    }

    sellers = mock_get_suppliers_with_expiring_documents()
    email_addresses = sellers[0]['email_addresses']

    send_document_expiry_campaign(client, sellers)

    segment_options = client.campaigns.create.call_args[1]['data']['recipients']['segment_opts']

    assert segment_options['match'] == 'any'
    assert len(segment_options['conditions']) == 3
    for condition in segment_options['conditions']:
        assert condition['condition_type'] == 'EmailAddress'
        assert condition['op'] == 'is'
        assert condition['field'] == 'EMAIL'
        assert condition['value'] in email_addresses


@mock.patch('app.tasks.mailchimp.suppliers.get_supplier_by_code')
@mock.patch('app.tasks.mailchimp.suppliers.get_suppliers_with_expiring_documents')
@mock.patch('app.tasks.mailchimp.MailChimp')
def test_document_expiry_campaign_adds_audit_event_on_success(
    mock_mailchimp,
    mock_get_suppliers_with_expiring_documents,
    mock_get_supplier_by_code,
    supplier,
    suppliers_with_expiring_documents
):
    client = MagicMock()
    mock_mailchimp.return_value = client
    mock_get_suppliers_with_expiring_documents.return_value = suppliers_with_expiring_documents
    mock_get_supplier_by_code.return_value = supplier

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    client.campaigns.create.return_value = {
        'id': 123
    }

    assert db.session.query(AuditEvent).count() == 0

    sellers = mock_get_suppliers_with_expiring_documents()
    send_document_expiry_campaign(client, sellers)

    audit_event = db.session.query(AuditEvent).first()
    assert audit_event.type == audit_types.sent_expiring_documents_email.value
    assert audit_event.data['campaign_title'] == ('Expiring documents - {}'
                                                  .format(date.today().isoformat()))
    assert audit_event.data['sellers'] == sellers


@mock.patch('app.tasks.mailchimp.suppliers.get_supplier_by_code')
@mock.patch('app.tasks.mailchimp.suppliers.get_suppliers_with_expiring_labour_hire_licences')
@mock.patch('app.tasks.mailchimp.MailChimp')
def test_licence_expiry_campaign_is_not_created_when_no_sellers_with_expiring_licences(
    mock_mailchimp,
    mock_get_suppliers_with_expiring_labour_hire_licences,
    mock_get_supplier_by_code,
    supplier
):
    client = MagicMock()
    mock_mailchimp.return_value = client
    mock_get_suppliers_with_expiring_labour_hire_licences.return_value = []
    mock_get_supplier_by_code.return_value = supplier

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    send_labour_hire_expiry_reminder()

    assert not client.campaigns.create.called
    assert not client.campaigns.content.update.called
    assert not client.campaigns.actions.schedule.called


@mock.patch('app.tasks.mailchimp.suppliers.get_supplier_by_code')
@mock.patch('app.tasks.mailchimp.suppliers.get_suppliers_with_expiring_labour_hire_licences')
@mock.patch('app.tasks.mailchimp.MailChimp')
def test_licence_expiry_campaign_is_not_created_if_audit_event_exists(
    mock_mailchimp,
    mock_get_suppliers_with_expiring_labour_hire_licences,
    mock_get_supplier_by_code,
    supplier,
    suppliers_with_expiring_labour_hire_licences,
    audit_events
):
    client = MagicMock()
    mock_mailchimp.return_value = client
    mock_get_suppliers_with_expiring_labour_hire_licences.return_value = suppliers_with_expiring_labour_hire_licences
    mock_get_supplier_by_code.return_value = supplier

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    send_labour_hire_expiry_reminder()

    assert not client.campaigns.create.called
    assert not client.campaigns.content.update.called
    assert not client.campaigns.actions.schedule.called


@mock.patch('app.tasks.mailchimp.suppliers.get_supplier_by_code')
@mock.patch('app.tasks.mailchimp.suppliers.get_suppliers_with_expiring_labour_hire_licences')
@mock.patch('app.tasks.mailchimp.MailChimp')
def test_licence_expiry_campaign_success(
    mock_mailchimp,
    mock_get_suppliers_with_expiring_labour_hire_licences,
    mock_get_supplier_by_code,
    supplier,
    suppliers_with_expiring_labour_hire_licences
):
    client = MagicMock()
    mock_mailchimp.return_value = client
    mock_get_suppliers_with_expiring_labour_hire_licences.return_value = suppliers_with_expiring_labour_hire_licences
    mock_get_supplier_by_code.return_value = supplier

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    client.campaigns.create.return_value = {
        'id': 123
    }

    send_labour_hire_expiry_reminder()

    assert client.campaigns.create.called
    assert client.campaigns.content.update.called
    assert client.campaigns.actions.schedule.called


@mock.patch('app.tasks.mailchimp.suppliers.get_supplier_by_code')
@mock.patch('app.tasks.mailchimp.suppliers.get_suppliers_with_expiring_labour_hire_licences')
@mock.patch('app.tasks.mailchimp.MailChimp')
def test_licence_expiry_campaign_is_created_with_segment_options(
    mock_mailchimp,
    mock_get_suppliers_with_expiring_labour_hire_licences,
    mock_get_supplier_by_code,
    supplier,
    suppliers_with_expiring_labour_hire_licences
):
    client = MagicMock()
    mock_mailchimp.return_value = client
    mock_get_suppliers_with_expiring_labour_hire_licences.return_value = suppliers_with_expiring_labour_hire_licences
    mock_get_supplier_by_code.return_value = supplier

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    client.campaigns.create.return_value = {
        'id': 123
    }

    sellers = mock_get_suppliers_with_expiring_labour_hire_licences()
    email_addresses = sellers[0]['email_addresses']

    send_labour_hire_licence_expiry_campaign(client, sellers)

    segment_options = client.campaigns.create.call_args[1]['data']['recipients']['segment_opts']

    assert segment_options['match'] == 'any'
    assert len(segment_options['conditions']) == 3
    for condition in segment_options['conditions']:
        assert condition['condition_type'] == 'EmailAddress'
        assert condition['op'] == 'is'
        assert condition['field'] == 'EMAIL'
        assert condition['value'] in email_addresses


@mock.patch('app.tasks.mailchimp.suppliers.get_supplier_by_code')
@mock.patch('app.tasks.mailchimp.suppliers.get_suppliers_with_expiring_labour_hire_licences')
@mock.patch('app.tasks.mailchimp.MailChimp')
def test_licence_expiry_campaign_adds_audit_event_on_success(
    mock_mailchimp,
    mock_get_suppliers_with_expiring_labour_hire_licences,
    mock_get_supplier_by_code,
    supplier,
    suppliers_with_expiring_labour_hire_licences
):
    client = MagicMock()
    mock_mailchimp.return_value = client
    mock_get_suppliers_with_expiring_labour_hire_licences.return_value = suppliers_with_expiring_labour_hire_licences
    mock_get_supplier_by_code.return_value = supplier

    environ['MAILCHIMP_MARKETPLACE_FOLDER_ID'] = '123456'
    environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

    client.campaigns.create.return_value = {
        'id': 123
    }

    assert db.session.query(AuditEvent).count() == 0

    sellers = mock_get_suppliers_with_expiring_labour_hire_licences()
    send_labour_hire_licence_expiry_campaign(client, sellers)

    audit_event = db.session.query(AuditEvent).first()
    assert audit_event.type == audit_types.sent_expiring_licence_email.value
    assert audit_event.data['campaign_title'] == ('Expiring labour hire licence - {}'
                                                  .format(date.today().isoformat()))
    assert audit_event.data['sellers'] == sellers
