from app.tasks.email import send_email
from botocore.exceptions import ClientError
from dmutils.email import EmailError


def test_send_email_celery_task_success(mocker):
    boto3 = mocker.patch('app.tasks.email.boto3')

    send_email(
        'testdemail.com',
        'This is a new test async email',
        'Test async email',
        'no-reply@marketplace.digital.gov.au',
        'Digital Marketplace'
    )

    assert boto3.client.called


def test_send_email_celery_task_fails_with_email_error(mocker):
    try:
        boto3 = mocker.patch('app.tasks.email.boto3')
        boto3.client.side_effect = ClientError({'Error': {'Code': 1, 'Message': "test failure"}}, 'Test')

        send_email(
            'testdemail.com',
            'This is a new test async email',
            'Test async email',
            'no-reply@marketplace.digital.gov.au',
            'Digital Marketplace'
        )
        assert False
    except EmailError as e:
        assert True
