import json


def test_existing_application_same_abn_as_applicant_at_signup(client, application_user):
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
            'user_type': user_role,
            'abn': '123456'
        }),
        content_type='application/json')

    assert response.status_code == 409
