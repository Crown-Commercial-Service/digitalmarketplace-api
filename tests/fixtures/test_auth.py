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
