import json
from nose.tools import assert_equal

test_seller = {
    'name': 'matt',
    'email_address': 'email+s@company.com',
    'user_type': 'seller'
}


def test_send_seller_type_signup_invite_email(client, mocker):
    send_email = mocker.patch('app.auth.views.users.send_account_activation_email')
    response = client.post(
        '/signup',
        data=json.dumps(test_seller),
        content_type='application/json')
    assert response.status_code == 200

    send_email.assert_called_once_with(
        email_address=test_seller['email_address'],
        name=test_seller['name'],
        user_type='seller'
    )


def test_send_buyer_type_signup_invite_email(client, mocker):
    send_email = mocker.patch('app.auth.views.users.send_account_activation_email')
    response = client.post(
        '/signup',
        data=json.dumps({
            'email_address': 'm@digital.gov.au',
            'name': 'Jeff Labowski',
            'user_type': 'buyer',
            'employment_status': 'employee'
        }),
        content_type='application/json')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Email invite sent successfully'

    send_email.assert_called_once_with(
        email_address='m@digital.gov.au',
        name='Jeff Labowski',
        user_type='buyer'
    )


def test_send_contractor_buyer_type_signup_invite_email(client, mocker):
    send_email = mocker.patch('app.auth.views.users.send_account_activation_manager_email')
    response = client.post(
        '/signup',
        data=json.dumps({
            'line_manager_email': 'm@danger.gov.au',
            'line_manager_name': 'Jeff Labowski',
            'employment_status': 'contractor',
            'user_type': 'buyer',
            'name': 'Royal',
            'email_address': 'rtenenabaum@mouse.gov.au'
        }),
        content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Email invite sent successfully'

    send_email.assert_called_once_with(
        manager_email='m@danger.gov.au',
        manager_name='Jeff Labowski',
        applicant_email='rtenenabaum@mouse.gov.au',
        applicant_name='Royal',
    )


def test_invalid_employment_status(client, mocker):
    response = client.post(
        '/signup',
        data=json.dumps({
            'line_manager_email': 'm@danger.gov.au',
            'line_manager_name': 'Jeff Labowski',
            'employment_status': 'nope',
            'user_type': 'buyer',
            'name': 'Royal',
            'email_address': 'rtenenabaum@mouse.gov.au'
        }),
        content_type='application/json')
    assert response.status_code == 400


def test_missing_name(client, mocker):
    response = client.post(
        '/signup',
        data=json.dumps({
            'email_address': 'm@goolag.com',
            'user_type': 'seller'
        }),
        content_type='application/json')
    assert response.status_code == 400


def test_signup_fails_without_required_fields(client, supplier_user):
    response = client.post(
        '/signup',
        data=json.dumps({
            'email_address': 'm@goolag.com',
            'name': 'Jeff Labowski'
        }),
        content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert_equal(data['message'], 'One or more required args were missing from the request')


def test_duplicate_supplier_with_same_domain(client, supplier_user):
    response = client.post(
        '/signup',
        data=json.dumps({
            'email_address': 'm@examplecompany.biz',
            'name': 'Jeff Labowski',
            'user_type': 'seller'
        }),
        content_type='application/json')
    assert response.status_code == 409
    data = json.loads(response.data)

    assert_equal(data['message'], 'An account with this email domain already exists')


def test_duplicate_application_with_same_domain(client, application_user):
    response = client.post(
        '/signup',
        data=json.dumps({
            'email_address': 'm@don.com',
            'name': 'Jeff Labowski',
            'user_type': 'seller'
        }),
        content_type='application/json')
    assert response.status_code == 409
    data = json.loads(response.data)
    assert_equal(data['message'], 'An account with this email domain already exists')


def test_generic_domain(client):
    response = client.post(
        '/signup',
        data=json.dumps({
            'email_address': 'm@gmail.com',
            'name': 'Jeff Labowski',
            'user_type': 'seller'
        }),
        content_type='application/json')
    assert response._status_code == 200

    data = json.loads(response.data)
    assert_equal(data['message'], 'Email invite sent successfully')
