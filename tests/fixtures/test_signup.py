import json
import pytest
import mock

from app.models import db, Agency, AgencyDomain
from app.api.services import user_claims_service
from nose.tools import assert_equal

test_seller = {
    'name': 'matt',
    'email_address': 'email+s@company.com',
    'user_type': 'seller'
}

gov_au_buyer = {
    'name': 'Indiana Jones',
    'email_address': 'indy+b@adventure.gov.au',
    'user_type': 'buyer'
}

whitelisted_non_gov_au_buyer = {
    'name': 'Han Solo',
    'email_address': 'solo+b@falcon.net.au',
    'user_type': 'buyer'
}

non_whitelisted_buyer_in_agency = {
    'name': 'Luke Skywalker',
    'email_address': 'luke+b@jedi.edu.au',
    'user_type': 'buyer'
}

non_whitelisted_buyer = {
    'name': 'Rick Deckard',
    'email_address': 'deckard+b@runner.com.au',
    'user_type': 'buyer'
}


@pytest.fixture()
def agencies(app, request):
    with app.app_context():
        db.session.add(Agency(
            id=1,
            name='Department of Adventure',
            domain='adventure.gov.au',
            category='Commonwealth',
            state='ACT',
            whitelisted=True,
            domains=[AgencyDomain(
                domain='adventure.gov.au',
                active=True
            )]
        ))

        db.session.add(Agency(
            id=2,
            name='Department of Millenium Falcons',
            domain='falcon.net.au',
            category='Commonwealth',
            state='NSW',
            whitelisted=True,
            domains=[AgencyDomain(
                domain='falcon.net.au',
                active=True
            )]
        ))

        db.session.add(Agency(
            id=3,
            name='Jedi Temple',
            domain='jedi.edu.au',
            category='State',
            state='NSW',
            whitelisted=False,
            domains=[AgencyDomain(
                domain='jedi.edu.au',
                active=True
            )]
        ))

        db.session.commit()

        yield Agency.query.all()


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_send_seller_type_signup_invite_email(user_claim, client, mocker):
    send_email = mocker.patch('app.api.views.users.send_account_activation_email')
    response = client.post(
        '/2/signup',
        data=json.dumps(test_seller),
        content_type='application/json')
    assert response.status_code == 200

    send_email.assert_called()


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_send_buyer_type_signup_invite_email(user_claim, client, mocker):
    send_email = mocker.patch('app.api.views.users.send_account_activation_email')
    response = client.post(
        '/2/signup',
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

    send_email.assert_called()


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_send_contractor_buyer_type_signup_invite_email(user_claim, client, mocker):
    send_email = mocker.patch('app.api.views.users.send_account_activation_manager_email')
    response = client.post(
        '/2/signup',
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

    send_email.assert_called()


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_invalid_employment_status(user_claim, client, mocker):
    response = client.post(
        '/2/signup',
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


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_missing_name(user_claim, client, mocker):
    response = client.post(
        '/2/signup',
        data=json.dumps({
            'email_address': 'm@goolag.com',
            'user_type': 'seller'
        }),
        content_type='application/json')
    assert response.status_code == 400


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_signup_fails_without_required_fields(user_claim, client, supplier_user):
    response = client.post(
        '/2/signup',
        data=json.dumps({
            'email_address': 'm@goolag.com',
            'name': 'Jeff Labowski'
        }),
        content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert_equal(data['message'], "'user_type' is a required property")


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_duplicate_supplier_with_same_domain(user_claim, client, supplier_user):
    response = client.post(
        '/2/signup',
        data=json.dumps({
            'email_address': 'm@examplecompany.biz',
            'name': 'Jeff Labowski',
            'user_type': 'seller'
        }),
        content_type='application/json')
    assert response.status_code == 409
    data = json.loads(response.data)

    assert_equal(data['message'], 'An account with this email domain already exists')


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_duplicate_application_with_same_domain(user_claim, client, application_user):
    response = client.post(
        '/2/signup',
        data=json.dumps({
            'email_address': 'm@don.com',
            'name': 'Jeff Labowski',
            'user_type': 'seller'
        }),
        content_type='application/json')
    assert response.status_code == 409
    data = json.loads(response.data)
    assert_equal(data['message'], 'An account with this email domain already exists')


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_generic_domain(user_claim, client):
    response = client.post(
        '/2/signup',
        data=json.dumps({
            'email_address': 'm@gmail.com',
            'name': 'Jeff Labowski',
            'user_type': 'seller',
            'url': '/2'
        }),
        content_type='application/json')
    assert response._status_code == 200

    data = json.loads(response.data)
    assert_equal(data['message'], 'Email invite sent successfully')


@mock.patch('app.tasks.publish_tasks.user_claim')
@pytest.mark.parametrize('user', [gov_au_buyer, whitelisted_non_gov_au_buyer])
def test_buyer_can_signup_with_whitelisted_email(user_claim, client, mocker, agencies, user):
    send_email = mocker.patch('app.api.views.users.send_account_activation_email')

    response = client.post(
        '/2/signup',
        data=json.dumps({
            'name': user['name'],
            'email_address': user['email_address'],
            'employment_status': 'employee',
            'user_type': user['user_type']
        }),
        content_type='application/json')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Email invite sent successfully'

    send_email.assert_called()


@mock.patch('app.tasks.publish_tasks.user_claim')
@pytest.mark.parametrize('user', [non_whitelisted_buyer_in_agency, non_whitelisted_buyer])
def test_buyer_can_not_signup_with_non_whitelisted_email(user_claim, client, mocker, agencies, user):
    response = client.post(
        '/2/signup',
        data=json.dumps({
            'name': user['name'],
            'email_address': user['email_address'],
            'employment_status': 'employee',
            'user_type': user['user_type']
        }),
        content_type='application/json')

    assert response.status_code == 403
    data = json.loads(response.data)
    assert data['message'] == 'A buyer account must have a valid government entity email domain'


@mock.patch('app.tasks.publish_tasks.user_claim')
def test_signup_creates_signup_claim_token(user_claim, app, client):
    response = client.post(
        '/2/signup',
        data=json.dumps({
            'email_address': 'm@digital.gov.au',
            'name': 'Jeff Labowski',
            'user_type': 'buyer',
            'employment_status': 'employee'
        }),
        content_type='application/json')
    assert response.status_code == 200

    with app.app_context():
        claim = user_claims_service.find(email_address='m@digital.gov.au', type='signup', claimed=False).one_or_none()
        assert claim.email_address == 'm@digital.gov.au'
