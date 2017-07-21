import json

test_seller = {
    'name': 'matt',
    'email_address': 'email+s@company.com',
}
test_buyer = {
    'name': 'matt',
    'email_address': 'email+b@company.com',
    'employment_status': 'employee'
}


def test_duplicate_supplier_with_same_domain(client):
    response = client.post(
        '/signup',
        data=json.dumps({
            'email_address': 'm@examplecompany.biz',
            'name': 'Jeff Labowski'
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
