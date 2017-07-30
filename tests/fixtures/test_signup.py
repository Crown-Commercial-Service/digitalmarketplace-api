import json

test_seller = {
    'name': 'matt',
    'email_address': 'email+s@company.com',
    'user_type': 'seller'
}
test_buyer = {
    'name': 'matt',
    'email_address': 'email+b@company.com',
    'employment_status': 'employee',
    'user_type': 'buyer'
}
test_contractor = {
    'line_manager_email': 'm@examplecompany.biz',
    'line_manager_name': 'Jeff Labowski',
    'employment_status': 'contractor',
    'user_type': 'buyer',
    'name': 'Royal',
    'email_address': 'rtenenabaum@ymca.org'
}


def test_duplicate_supplier_with_same_domain(client):
    response = client.post(
        '/signup',
        data=json.dumps({
            'email_address': 'm@examplecompany.biz',
            'name': 'Jeff Labowski',
            'user_type': 'seller'
        }),
        content_type='application/json')
    assert response.status_code == 200


def test_send_seller_type_signup_invite_email(client, mocker):
    send_email = mocker.patch('app.auth.views.send_account_activation_email')
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
    send_email = mocker.patch('app.auth.views.send_account_activation_email')
    response = client.post(
        '/signup',
        data=json.dumps(test_buyer),
        content_type='application/json')
    assert response.status_code == 200

    send_email.assert_called_once_with(
        email_address=test_buyer['email_address'],
        name=test_buyer['name'],
        user_type='buyer'
    )


def test_send_contractor_buyer_type_signup_invite_email(client, mocker):
    send_email = mocker.patch('app.auth.views.send_account_activation_manager_email')
    response = client.post(
        '/signup',
        data=json.dumps(test_contractor),
        content_type='application/json')
    assert response.status_code == 200

    send_email.assert_called_once_with(
        manager_email=test_contractor['line_manager_email'],
        manager_name=test_contractor['line_manager_name'],
        applicant_email=test_contractor['email_address'],
        applicant_name=test_contractor['name'],
    )
