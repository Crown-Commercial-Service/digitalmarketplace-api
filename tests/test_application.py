"""
Tests for the application infrastructure
"""
from flask import json
import pytest

from tests.bases import BaseApplicationTest


class TestApplication(BaseApplicationTest):
    def test_index(self):
        response = self.client.get('/')
        assert response.status_code == 200
        assert 'links' in json.loads(response.get_data())

    def test_404(self):
        response = self.client.get('/not-found')
        assert response.status_code == 404

    def test_bearer_token_is_required(self):
        """Stop the client from sending an auth header and assert response is 401 Unauthorised."""
        self.app.wsgi_app.kwargs.pop('HTTP_AUTHORIZATION')
        response = self.client.get('/')

        assert response.status_code == 401
        assert 'WWW-Authenticate' in response.headers

    @pytest.mark.parametrize('endpoint, token, unauthorized',
                             (
                                 ('/', 'bad-token', True),
                                 ('/', 'myToken', False),  # Main API token succeeds
                                 ('/', 'myCallbackToken', True),  # Callback API token fails
                                 ('/callbacks', 'bad-token', True),
                                 ('/callbacks', 'myToken', True),  # Main API token fails
                                 ('/callbacks', 'myCallbackToken', False),  # Callback API token succeeds
                             ))
    def test_invalid_bearer_token_is_not_allowed(self, endpoint, token, unauthorized):
        """Force the client to send an invalid auth header and assert response is 403 Forbidden."""
        self.app.wsgi_app.kwargs['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        response = self.client.get(endpoint)

        if unauthorized:
            assert response.status_code == 403

        else:
            assert response.status_code == 200

    def test_max_age_is_one_day(self):
        response = self.client.get('/')
        assert 86400 == response.cache_control.max_age
