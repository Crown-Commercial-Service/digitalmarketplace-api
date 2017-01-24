"""
Tests for the application infrastructure
"""
from flask import json
from nose.tools import assert_equal

from tests.bases import BaseApplicationTest


class TestApplication(BaseApplicationTest):
    def test_index(self):
        response = self.client.get('/')
        assert 200 == response.status_code
        assert 'links' in json.loads(response.get_data())

    def test_404(self):
        response = self.client.get('/not-found')
        assert 404 == response.status_code

    def test_bearer_token_is_required(self):
        self.do_not_provide_access_token()
        response = self.client.get('/')
        assert 401 == response.status_code
        assert 'WWW-Authenticate' in response.headers

    def test_invalid_bearer_token_is_required(self):
        self.do_not_provide_access_token()
        response = self.client.get(
            '/',
            headers={'Authorization': 'Bearer invalid-token'})
        assert 403 == response.status_code

    def test_max_age_is_one_day(self):
        response = self.client.get('/')
        assert_equal(86400, response.cache_control.max_age)
