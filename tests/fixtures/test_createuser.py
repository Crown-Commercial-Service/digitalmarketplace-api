import json


def test_existing_application_same_organisation_as_applicant_at_signup(client, mocker, application_user):
    send_email = mocker.patch('app.api.user.send_existing_application_notification')
    existing_user = application_user

    existing_user_domain = existing_user.email_address.split('@')[-1]

    user_role = 'seller'
    user_email = 'es@{}'.format(existing_user_domain)
    user_name = 'new applicant creating duplicate appication'

    response = client.post(
        '/2/signup',
        data=json.dumps({
            'name': user_name,
            'email_address': user_email,
            'password': 'pa$$werd1',
            'user_type': user_role
        }),
        content_type='application/json')

    assert response.status_code == 409
    data = json.loads(response.data)
    assert data['message'] == (
        "An account with this email domain already exists")

    send_email.assert_called_once_with(
        application_id=existing_user.application_id,
        email_address='es@{}'.format(existing_user_domain)
    )
