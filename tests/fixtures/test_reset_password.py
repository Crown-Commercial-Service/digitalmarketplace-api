import json
import mock
from app import encryption
from app.models import User
from app.api.services import user_claims_service
from dmutils.email import InvalidToken


def _create_token(client, email_address, framework='digital-marketplace'):
    token_response = client.post(
        '/2/reset-password',
        data=json.dumps({
            'email_address': email_address,
            'framework': framework
        }),
        content_type='application/json'
    )
    return token_response


def _get_token(email_address):
    return user_claims_service.find(type='password_reset').first()


@mock.patch('app.tasks.publish_tasks.user_claim')
@mock.patch('app.api.views.users.key_values_service')
def test_reset_password(key_values_service, user_claim, client, app, users, mocker):
    with app.app_context():
        user = users[1]
        token_response = _create_token(client, user.email_address)
        assert token_response.status_code == 200
        claim = _get_token(user.email_address)

        old_password = user.password
        new_password = 'pa$$werd1'

        assert old_password != new_password

        key_values_service.get_by_key.return_value = {'data': {'age': 3600}}

        response = client.post(
            '/2/reset-password/{}?e={}'.format(claim.token, user.email_address),
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


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_reset_password_fails_invalid_token(user_claim, client, app, users):
    with app.app_context():
        user = users[2]
        fake_token = 'ahsdfsadfnotavalidtokenstring984t9uthu99a03ihwe0ih'
        response = client.post(
            '/2/reset-password/{}?e={}'.format(fake_token, user.email_address),
            data=json.dumps({
                'email_address': user.email_address,
                'user_id': user.id,
                'password': 'pa$$werd1',
                'confirmPassword': 'pa$$werd1'
            }),
            content_type='application/json')
        assert response.status_code == 400


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_reset_password_passwords_dont_match(user_claim, client, app, users):
    with app.app_context():
        user = users[2]
        token_response = _create_token(client, user.email_address, 'digital-marketplace')
        claim = _get_token(user.email_address)
        response = client.post(
            '/2/reset-password/{}?e={}'.format(claim.token, user.email_address),
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


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_reset_password_requires_all_of_the_args(user_claim, client, app, users):
    with app.app_context():
        user = users[2]
        token_response = _create_token(client, user.email_address)
        claim = _get_token(user.email_address)

        response = client.post(
            '/2/reset-password/{}?e={}'.format(claim.token, user.email_address),
            data=json.dumps({
                'email_address': user.email_address,
                'user_id': user.id
            }),
            content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['message'] == 'One or more required args were missing from the request'


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_send_marketplace_reset_password_email(user_claim, client, app, mocker, users):
    with app.app_context():
        user = users[3]
        framework = 'digital-marketplace'
        send_email = mocker.patch('app.api.views.users.send_reset_password_confirm_email')
        response = _create_token(client, user.email_address)
        claim = _get_token(user.email_address)
        assert response.status_code == 200

        send_email.assert_called_once_with(
            token=claim.token,
            email_address=user.email_address,
            locked=user.locked,
            framework=framework
        )
