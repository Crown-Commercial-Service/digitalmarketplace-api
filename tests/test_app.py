from .helpers import with_application, provide_access_token


@with_application
@provide_access_token
def test_index(app):
    response = app.get('/')
    assert u'Hello You Dogs' in response.data.decode('utf8')


@with_application
@provide_access_token
def test_404(app):
    response = app.get('/not-found')
    assert u'<h1>404</h1>' in response.data.decode('utf8')


@with_application
def test_bearer_token_is_required(app):
    response = app.get('/')
    assert 401 == response.status_code
    assert 'WWW-Authenticate' in response.headers


@with_application
def test_invalid_bearer_tokens_not_allowed(app):
    response = app.get('/', headers={'Authorization': 'Bearer invalid-token'})
    assert 403 == response.status_code
