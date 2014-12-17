from functools import wraps
import os

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

        # set up valid-token as a valid token
        auth_tokens = os.environ.get('AUTH_TOKENS')
        os.environ['AUTH_TOKENS'] = 'valid-token'

        result = func(app)

        if auth_tokens is None:
            del os.environ['AUTH_TOKENS']
        else:
            os.environ['AUTH_TOKENS'] = auth_tokens

        return result

    return wrapped
