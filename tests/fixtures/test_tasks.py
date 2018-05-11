from app.tasks.mailchimp import sync_mailchimp_seller_list, MailChimpConfigException, send_new_briefs_email
from app.tasks.s3 import create_resumes_zip, CreateResumesZipException
from app.models import AuditEvent
from app import db
from dmapiclient.audit import AuditTypes
from requests.exceptions import RequestException
from os import environ
from mock.mock import MagicMock
from datetime import date
from tests.app.helpers import COMPLETE_DIGITAL_SPECIALISTS_BRIEF
import pytest


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
    emails_to_subscribe = user_emails + supplier_emails

    mailchimp.return_value = client

    with app.app_context():
        environ['MAILCHIMP_SELLER_LIST_ID'] = '123456'

        client.lists.members.all.return_value = list_response

        sync_mailchimp_seller_list()

        client.lists.members.all.assert_called_with('123456', fields='members.email_address,members.id', get_all=True)
        for email in emails_to_subscribe:
            client.lists.members.create.assert_any_call(
                '123456',
                data={'email_address': email, 'status': 'subscribed'}
            )


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
def test_create_resumes_zip_success(app, briefs, brief_responses, mocker):
    boto3 = mocker.patch('app.tasks.s3.boto3')
    s3 = MagicMock()
    bucket = MagicMock()

    boto3.resource.return_value = s3
    s3.Bucket.return_value = bucket

    with app.app_context():
        create_resumes_zip(1)
        assert boto3.resource.called
        assert s3.Bucket.called
        assert bucket.download_fileobj.called
        assert bucket.upload_fileobj.called


brief_response_data = {
    'attachedDocumentURL': []
}


@pytest.mark.parametrize('brief_responses', [{'data': brief_response_data}], indirect=True)
def test_create_resumes_zip_fails_when_no_attachments(app, briefs, brief_responses, mocker):
    boto3 = mocker.patch('app.tasks.s3.boto3')
    s3 = MagicMock()
    bucket = MagicMock()

    boto3.resource.return_value = s3
    s3.Bucket.return_value = bucket

    with app.app_context():
        try:
            create_resumes_zip(1)
            assert False
        except CreateResumesZipException as e:
            assert boto3.resource.called
            assert s3.Bucket.called
            assert not bucket.download_fileobj.called
            assert not bucket.upload_fileobj.called
            assert str(e) == 'The brief id "1" did not have any attachments'
