import json
from urllib import quote
from app import encryption
from app.models import User
from dmutils.email import InvalidToken


def _create_token(client, email_address, framework='digital-marketplace'):
    token_response = client.post(
        '/2/reset-password/framework/{}'.format(framework),
        data=json.dumps({
            'email_address': email_address
        }),
        content_type='application/json'
    )
    return token_response


def test_marketplace_reset_password_token_creation(client, users):
    user = users[0]
    token_response = _create_token(client, user.email_address, 'digital-marketplace')
    assert token_response.status_code == 200
    assert json.loads(token_response.data)['token'] is not None


def test_return_user_data_from_reset_password_token(client, users):
    user = users[4]
    response = _create_token(client, user.email_address)
    token = json.loads(response.data)['token']

    validate_token_response = client.get(
        '/2/reset-password/{}'.format(token),
        content_type='application/json'
    )

    assert validate_token_response.status_code == 200

    data = json.loads(response.data)

    assert data['token'] == token
    assert data['email_address'] == user.email_address


def test_reset_password(client, users):
    user = users[1]
    token_response = _create_token(client, user.email_address)
    assert token_response.status_code == 200
    token = json.loads(token_response.data)['token']

    old_password = user.password
    new_password = 'pa$$werd1'

    assert old_password != new_password

    response = client.post(
        '/2/reset-password/{}'.format(token),
        data=json.dumps({
            'email_address': user.email_address,
            'user_id': user.id,
            'password': 'pa$$werd1',
            'confirmPassword': 'pa$$werd1'
        }),
        content_type='application/json')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'User with email {}, successfully updated their password'.format(user.email_address)

    user = User.query.filter(
        User.email_address == user.email_address).first()

    assert encryption.authenticate_user(new_password, user)
    assert not encryption.authenticate_user(old_password, user)


def test_reset_password_fails_invalid_token(client, users):
    user = users[2]
    fake_token = 'ahsdfsadfnotavalidtokenstring984t9uthu99a03ihwe0ih'
    try:
        response = client.post(
            '/2/reset-password/{}'.format(fake_token),
            data=json.dumps({
                'email_address': user.email_address,
                'user_id': user.id,
                'password': 'pa$$werd1',
                'confirmPassword': 'pa$$werd1'
            }),
            content_type='application/json')
        assert response.status_code == 400
    except Exception as error:
        assert isinstance(error, InvalidToken)


def test_reset_password_passwords_dont_match(client, users):
    user = users[2]
    fake_token = 'ahsdfsadfnotavalidtokenstring984t9uthu99a03ihwe0ih'
    response = client.post(
        '/2/reset-password/{}'.format(fake_token),
        data=json.dumps({
            'email_address': user.email_address,
            'user_id': user.id,
            'password': 'pa$$werd1',
            'confirmPassword': 'pa$$twerk1'
        }),
        content_type='application/json')

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['message'] == 'Passwords do not match'


def test_reset_password_requires_all_of_the_args(client, users):
    user = users[2]
    token_response = _create_token(client, user.email_address)
    token = json.loads(token_response.data)['token']

    response = client.post(
        '/2/reset-password/{}'.format(token),
        data=json.dumps({
            'email_address': user.email_address,
            'user_id': user.id
        }),
        content_type='application/json')

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['message'] == 'One or more required args were missing from the request'


def test_send_marketplace_reset_password_email(client, app, mocker, users):
    with app.app_context():
        user = users[3]
        framework = 'digital-marketplace'
        send_email = mocker.patch('app.api.views.users.send_reset_password_confirm_email')
        response = _create_token(client, user.email_address)
        token = json.loads(response.data)['token']
        assert response.status_code == 200

        reset_password_url = '{}{}/reset-password/{}'.format(
            app.config['FRONTEND_ADDRESS'],
            app.config['APP_ROOT'].get(framework),
            quote(token)
        )

        send_email.assert_called_once_with(
            email_address=user.email_address,
            url=reset_password_url,
            locked=user.locked,
            framework=framework
        )
