from __future__ import absolute_import

import os
from nose.tools import assert_equal

from app import create_app, db


class WSGIApplicationWithEnvironment(object):
    def __init__(self, app, **kwargs):
        self.app = app
        self.kwargs = kwargs

    def __call__(self, environ, start_response):
        for key, value in self.kwargs.items():
            environ[key] = value
        return self.app(environ, start_response)


class BaseApplicationTest(object):
    def setup(self):
        self.app = create_app('test')
        self.client = self.app.test_client()

        self.setup_authorization()
        self.setup_database()

    def setup_authorization(self):
        """Set up bearer token and pass on all requests"""
        valid_token = 'valid-token'
        self.app.wsgi_app = WSGIApplicationWithEnvironment(
            self.app.wsgi_app,
            HTTP_AUTHORIZATION='Bearer {}'.format(valid_token))
        self._auth_tokens = os.environ.get('AUTH_TOKENS')
        os.environ['AUTH_TOKENS'] = valid_token

    def do_not_provide_access_token(self):
        self.app.wsgi_app = self.app.wsgi_app.app

    def setup_database(self):
        with self.app.app_context():
            db.create_all()

    def teardown(self):
        self.teardown_authorization()
        self.teardown_database()

    def teardown_authorization(self):
        if self._auth_tokens is None:
            del os.environ['AUTH_TOKENS']
        else:
            os.environ['AUTH_TOKENS'] = self._auth_tokens

    def teardown_database(self):
        with self.app.app_context():
            db.drop_all()


class JSONUpdateTestMixin(object):
    """
    Tests to verify that endpoints that accept JSON.
    """
    endpoint = None
    method = None
    client = None

    def test_non_json_causes_failure(self):
        response = self.client.open(
            self.endpoint,
            method=self.method,
            data='this is not JSON',
            content_type='application/json')

        assert_equal(response.status_code, 400)

    def test_invalid_json_causes_failure(self):
        response = self.client.open(
            self.endpoint,
            method=self.method,
            data='{"not": "valid"}',
            content_type='application/json')

        assert_equal(response.status_code, 400)

    def test_invalid_content_type_causes_failure(self):
        response = self.client.open(
            self.endpoint,
            method=self.method,
            data='{"services": {"foo": "bar"}}')

        assert_equal(response.status_code, 400)