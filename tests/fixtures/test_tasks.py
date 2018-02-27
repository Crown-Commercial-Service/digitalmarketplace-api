from app.tasks.mailchimp import sync_mailchimp_seller_list, MailChimpConfigException
from requests.exceptions import RequestException
from os import environ
from mock.mock import MagicMock
import pytest


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
