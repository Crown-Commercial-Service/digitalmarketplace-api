from functools import wraps

from app import create_app


def with_application(func):
    app = create_app('test').test_client()

    @wraps(func)
    def wrapped():
        return func(app)

    return wrapped


def provide_access_token(func):
    """Inject a valid Authorization header for testing"""
    @wraps(func)
    def wrapped(app):
        def method_wrapper(original):
            def wrapped(*args, **kwargs):
                headers = kwargs.get('headers', {})
                headers['Authorization'] = 'Bearer valid-token'
                kwargs['headers'] = headers
                return original(*args, **kwargs)
            return wrapped

        http_methods = (app.get, app.post, app.put, app.delete)
        (app.get, app.post, app.put, app.delete) = map(
            method_wrapper, http_methods)

        return func(app)

    return wrapped


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
