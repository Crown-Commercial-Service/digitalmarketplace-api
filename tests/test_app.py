from functools import wraps

from app import create_app


def with_app(func):
    app = create_app('test').test_client()

    @wraps(func)
    def wrapped():
        return func(app)

    return wrapped


@with_app
def test_index(app):
    response = app.get('/')
    assert 'Hello You Dogs' in response.data


@with_app
def test_404(app):
    response = app.get('/not-found')
    assert '<h1>404</h1>' in response.data
