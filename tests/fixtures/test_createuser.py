import json
from app.api.helpers import generate_creation_token
from app.models import User


def test_signup_handles_valid_token(client, users):
    user = users[0]
    token = generate_creation_token(
        name=user.name,
        email_address=user.email_address,
        user_type=user.role,
        framework='digital-marketplace'
    )

    response = client.get(
        '/2/tokens/{}'.format(token),
        content_type='application/json')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['name'] == user.name
    assert data['email_address'] == user.email_address
    assert data['user_type'] == user.role
    assert data['framework'] == 'digital-marketplace'


def test_send_buyer_invite_invalid_token(client):
    fake_token = 'ahsdfsadfnotavalidtokenstring984t9uthu99a03ihwe0ih'
    response = client.get(
        '/2/tokens/{}'.format(fake_token),
        content_type='application/json')

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['message'] == 'The token provided is invalid. It may have expired'


def test_create_user(client, app, applications, agencies):
    with app.app_context():
        user_role = 'buyer'
        user_email = 'es@asdf.gov.au'
        user_name = 'new buyer with supplier code'

        response = client.post(
            '/2/users',
            data=json.dumps({
                'name': user_name,
                'email_address': user_email,
                'password': 'pa$$werd1',
                'user_type': user_role,
                'framework': 'digital-marketplace'
            }),
            content_type='application/json')
        assert response.status_code == 200
        fetched_user = User.query.filter(
            User.email_address == user_email.lower()).first()

        assert fetched_user is not None
        assert fetched_user.name == user_name


def test_create_whitelisted_user(client, app, applications, agencies):
    with app.app_context():
        user_role = 'buyer'
        user_email = 'es@asdf.com.au'
        user_name = 'new buyer with supplier code'

        response = client.post(
            '/2/users',
            data=json.dumps({
                'name': user_name,
                'email_address': user_email,
                'password': 'pa$$werd1',
                'user_type': user_role,
                'framework': 'digital-marketplace'
            }),
            content_type='application/json')
        assert response.status_code == 200
        fetched_user = User.query.filter(
            User.email_address == user_email.lower()).first()

        assert fetched_user is not None
        assert fetched_user.name == user_name

        response = client.post(
            '/2/users',
            data=json.dumps({
                'name': user_name,
                'email_address': 'es@zzzz.com.au',
                'password': 'pa$$werd1',
                'user_type': user_role,
                'framework': 'digital-marketplace'
            }),
            content_type='application/json')
        assert response.status_code == 400


def test_should_require_minimum_args(client):
    response = client.post(
        '/2/users',
        data=json.dumps({
            'name': 'Jeff Labowski',
            'email_address': 'm@examplecompany.biz',
            'password': 'pa$$werd1'
            # 'user_type': 'seller'
        }),
        content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['message'] == "'user_type' is a required property"


def test_create_user_wont_create_duplicate_user(client, users):
    user = users[0]
    response = client.post(
        '/2/users',
        data=json.dumps({
            'name': user.name,
            'email_address': user.email_address,
            'password': 'pa$$werd1',
            'user_type': user.role
        }),
        content_type='application/json')

    assert response.status_code == 409


def test_create_user_without_data_paylaod(client):
    response = client.post(
        '/2/users',
        content_type='application/json')

    assert response.status_code == 400


def test_supplier_role_should_have_supplier_code(client, supplier_user):
    response = client.post(
        '/2/users',
        data=json.dumps({
            'name': 'new supplier',
            'email_address': 'supplier_user email_address',
            'password': 'pa$$werd1',
            'user_type': 'supplier',
            'supplier_code': None
        }),
        content_type='application/json')

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['message'] == "'supplier_code' is required for users with 'supplier' role"


def test_non_supplier_role_should_not_have_supplier_code(client):
    user_role = 'buyer'
    user_email = 'es@asdf.gov.au'
    user_name = 'new buyer with supplier code'

    response = client.post(
        '/2/users',
        data=json.dumps({
            'name': user_name,
            'email_address': user_email,
            'password': 'pa$$werd1',
            'user_type': user_role,
            'supplier_code': 234
        }),
        content_type='application/json')

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['message'] == "'supplier_code' is only valid for users with 'supplier' role, not '{}'".format(user_role)


def test_applicant_requires_app_id_property(client, applications):
    application_id = applications[0].id
    user_role = 'applicant'
    user_email = 'es@asdf.gov.au'
    user_name = 'new buyer with supplier code'

    response = client.post(
        '/2/users',
        data=json.dumps({
            'name': user_name,
            'email_address': user_email,
            'password': 'pa$$werd1',
            'user_type': user_role,
            'application_id': application_id,
            'framework': 'digital-marketplace'
        }),
        content_type='application/json')

    assert response.status_code == 200
    fetched_user = User.query.filter(
        User.email_address == user_email.lower()).first()

    assert fetched_user is not None
    assert fetched_user.application_id == application_id


def test_create_user_with_invalid_app_id_property(client, app, applications):
    with app.app_context():
        user_role = 'seller'
        user_email = 'es@blah.com'
        user_name = 'new seller'

        response = client.post(
            '/2/users',
            data=json.dumps({
                'name': user_name,
                'email_address': user_email,
                'password': 'pa$$werd1',
                'user_type': user_role,
                'application_id': 23452345
            }),
            content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['message'] == 'An invalid application id was passed to create new user api'


def test_buyer_cant_set_application_id_property(client, applications):
    application_id = applications[0].id
    user_role = 'buyer'
    user_email = 'es@asdf.gov.au'
    user_name = 'new buyer with supplier code'

    response = client.post(
        '/2/users',
        data=json.dumps({
            'name': user_name,
            'email_address': user_email,
            'password': 'pa$$werd1',
            'user_type': user_role,
            'application_id': application_id
        }),
        content_type='application/json')

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['message'] == (
        "'application_id' is only valid for users with applicant' or 'supplier' role, not '{}'".format(user_role))


def test_existing_application_same_organisation_as_applicant(client, mocker, applications):
    existing_application = applications[0]

    existing_application_email = existing_application.data.get('email', None)
    existing_application_email = 'es@covfefe.com' if existing_application_email is None else existing_application_email
    existing_application_domain = existing_application_email.split('@')[-1]

    user_role = 'seller'
    user_email = 'es@{}'.format(existing_application_domain)
    user_name = 'new applicant creating duplicate appication'

    response = client.post(
        '/2/users',
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
        "An application with this email address already exists")


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


def test_send_invite(client, users):
    user = users[0]
    token = generate_creation_token(
        name=user.name,
        email_address=user.email_address,
        user_type=user.role,
        framework='digital-marketplace'
    )

    response = client.post(
        '/2/send-invite/{}'.format(token),
        content_type='application/json')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['email_address'] == user.email_address
