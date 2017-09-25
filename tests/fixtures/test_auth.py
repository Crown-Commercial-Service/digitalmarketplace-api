import json


def test_anonymous(client):
    res = client.get('/ping')
    data = json.loads(res.get_data(as_text=True))

    assert not data['isAuthenticated']

    res = client.get('/_protected')
    assert res.status_code == 401


def test_authenticated(client, login):
    client.get('/auto-login')
    res = client.get('/ping')
    data = json.loads(res.get_data(as_text=True))

    assert data['isAuthenticated']

    res = client.get('/_protected')
    assert res.status_code == 200


def test_valid_csrf(app, client):
    app.config['CSRF_ENABLED'] = True
    res = client.get('/ping')
    data = json.loads(res.get_data(as_text=True))
    res = client.post('/_post', headers={'X-CSRFToken': data['csrfToken']})
    assert res.status_code == 200


def test_invalid_csrf(app, client):
    app.config['CSRF_ENABLED'] = True
    res = client.post('/_post')
    assert res.status_code == 400


def test_logout(client, login):
    client.get('/auto-login')
    res = client.get('/ping')
    data = json.loads(res.get_data(as_text=True))

    assert data['isAuthenticated']

    res = client.get('/_protected')
    assert res.status_code == 200

    res = client.get('/logout')
    assert res.status_code == 200

    res = client.get('/_protected')
    assert res.status_code == 401

    res = client.get('/ping')
    data = json.loads(res.get_data(as_text=True))
    assert not data['isAuthenticated']

    res = client.get('/logout')
    assert res.status_code == 401


def test_login(client, users):
    res = client.post('/login')
    assert res.status_code == 400

    res = client.post('/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpasswor'
    }), content_type='application/json')
    assert res.status_code == 403


def test_profile_supplier(client, supplier_user):
    res = client.get('/supplier')
    assert res.status_code == 401

    res = client.post('/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.get('/supplier')
    assert res.status_code == 200
    data = json.loads(res.get_data(as_text=True))
    assert data['user']
    assert data['user']


def test_profile_buyer(client, users):
    res = client.post('/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpassword',
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.get('/supplier')
    assert res.status_code == 401
