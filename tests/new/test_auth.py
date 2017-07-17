import json


def test_anonymous(client):
    res = client.get('/ping')
    data = json.loads(res.get_data(as_text=True))

    assert not data['isAuthenticated']

    res = client.get('/protected')
    assert res.status_code == 401


def test_authenticated(client, login):
    client.get('/auto-login')
    res = client.get('/ping')
    data = json.loads(res.get_data(as_text=True))

    assert data['isAuthenticated']

    res = client.get('/protected')
    assert res.status_code == 200
