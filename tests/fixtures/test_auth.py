import json
from base64 import b64encode


def test_anonymous(client):
    res = client.get('/2/ping')
    data = json.loads(res.get_data(as_text=True))

    assert not data['isAuthenticated']

    res = client.get('/2/_protected')
    assert res.status_code == 401


def test_authenticated(client, users):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    res = client.get('/2/ping')
    data = json.loads(res.get_data(as_text=True))

    assert data['isAuthenticated']

    res = client.get('/2/_protected')
    assert res.status_code == 200


def test_basic_auth(client, users):
    header = b64encode('{}:{}'.format('test@digital.gov.au', 'testpassword'))
    res = client.get('/2/_protected', headers={'Authorization': 'Basic {}'.format(header)})
    assert res.status_code == 200

    wrong_password = b64encode('{}:{}'.format('test@digital.gov.au', 'testpasswor'))
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
