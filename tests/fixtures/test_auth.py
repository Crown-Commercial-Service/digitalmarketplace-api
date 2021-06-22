import json
import pytest
from base64 import b64encode


def test_anonymous(client):
    res = client.get('/2/ping')
    data = json.loads(res.get_data(as_text=True))

    assert not data['isAuthenticated']

    res = client.get('/2/_protected')
    assert res.status_code == 401


def test_authenticated(client, users):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au',
        'password': 'testpassword'
    }), content_type='application/json')

    res = client.get('/2/ping')
    data = json.loads(res.get_data(as_text=True))

    assert data['isAuthenticated']

    res = client.get('/2/_protected')
    assert res.status_code == 200


def test_basic_auth(client, users):
    header = b64encode('{}:{}'.format('test@digital.gov.au', 'testpassword').encode()).decode()
    res = client.get('/2/_protected', headers={'Authorization': 'Basic {}'.format(header)})
    assert res.status_code == 200

    wrong_password = b64encode('{}:{}'.format('test@digital.gov.au', 'testpasswor').encode()).decode()
    res = client.get('/2/_protected', headers={'Authorization': 'Basic {}'.format(wrong_password)})
    assert res.status_code == 401


def test_valid_csrf(app, client):
    app.config['CSRF_ENABLED'] = True
    res = client.get('/2/ping')
    data = json.loads(res.get_data(as_text=True))
    res = client.post('/2/_post', headers={'X-CSRFToken': data['csrfToken']})
    assert res.status_code == 200


def test_invalid_csrf(app, client):
    app.config['CSRF_ENABLED'] = True
    res = client.post('/2/_post')
    assert res.status_code == 400


def test_logout(client, users):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    res = client.get('/2/ping')

    data = json.loads(res.get_data(as_text=True))

    assert data['isAuthenticated']

    res = client.get('/2/_protected')
    assert res.status_code == 200

    res = client.get('/2/logout')
    assert res.status_code == 200

    res = client.get('/2/_protected')
    assert res.status_code == 401

    res = client.get('/2/ping')
    data = json.loads(res.get_data(as_text=True))
    assert not data['isAuthenticated']

    res = client.get('/2/logout')
    assert res.status_code == 401


def test_login(client, users):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au'
    }), content_type='application/json')
    assert res.status_code == 400

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpasswor'
    }), content_type='application/json')
    assert res.status_code == 403


def test_api_key_generating_by_admin(client, users, admin_users):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'testadmin@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/generate-api-key/1')
    assert res.status_code == 200

    data = json.loads(res.get_data())
    assert len(data['key']) == 64


def test_api_key_authentication(client, users, api_key):
    key = api_key.key

    res = client.get('/2/ping')
    data = json.loads(res.get_data(as_text=True))
    assert not data['isAuthenticated']

    res = client.get('/2/ping', headers={'X-Api-Key': key})
    data = json.loads(res.get_data(as_text=True))
    assert data['isAuthenticated']


def test_api_key_authentication_fails_on_non_api_key_resource(client, users, api_key):
    key = api_key.key

    res = client.get('/2/_protected', headers={'X-Api-Key': key})
    assert res.status_code == 401


def test_api_key_authentication_fails_supplier_user(client, supplier_user):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.get('/2/ping')
    data = json.loads(res.get_data(as_text=True))
    assert data['isAuthenticated']

    res = client.post('/2/generate-api-key/{}'.format(supplier_user.id))
    assert res.status_code == 403


def test_api_key_authentication_fails_buyer_user(client, users):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.get('/2/ping')
    data = json.loads(res.get_data(as_text=True))
    assert data['isAuthenticated']

    res = client.post('/2/generate-api-key/7')
    assert res.status_code == 403


def test_api_key_authentication_fails_bad_header(client, users, api_key):
    key = api_key.key

    res = client.get('/2/ping')
    data = json.loads(res.get_data(as_text=True))
    assert not data['isAuthenticated']

    res = client.get('/2/ping', headers={'X-Apikey': key})
    data = json.loads(res.get_data(as_text=True))
    assert not data['isAuthenticated']

    res = client.get('/2/ping', headers={'X-Api-key': 'badkey'})
    assert res.status_code == 403


def test_api_key_revocation(client, users, api_key):
    key = api_key.key

    res = client.get('/2/ping')
    data = json.loads(res.get_data(as_text=True))
    assert not data['isAuthenticated']

    res = client.get('/2/ping', headers={'X-Api-Key': key})
    data = json.loads(res.get_data(as_text=True))
    assert data['isAuthenticated']

    res = client.post('/2/revoke-api-key/{}'.format(key))
    assert res.status_code == 200

    res = client.get('/2/ping', headers={'X-Api-Key': key})
    assert res.status_code == 403


def test_api_key_revocation_by_admin(client, users, admin_users, api_key):
    key = api_key.key

    res = client.get('/2/ping')
    data = json.loads(res.get_data(as_text=True))
    assert not data['isAuthenticated']

    res = client.get('/2/ping', headers={'X-Api-Key': key})
    data = json.loads(res.get_data(as_text=True))
    assert data['isAuthenticated']

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'testadmin@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/revoke-api-key/{}'.format(key))
    assert res.status_code == 200

    res = client.get('/2/logout')
    assert res.status_code == 200

    res = client.get('/2/ping', headers={'X-Api-Key': key})
    assert res.status_code == 403


def test_api_key_require_auth_decorator(client, users, api_key):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.get('/2/reports/brief/published')
    assert res.status_code == 403

    key = api_key.key

    res = client.get('/2/reports/brief/published', headers={'X-Api-Key': key})
    assert res.status_code == 200
