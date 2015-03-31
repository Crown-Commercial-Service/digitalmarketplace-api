from flask import json
from nose.tools import assert_equal, assert_in, assert_not_equal, \
    assert_almost_equal

from app import db
from app.models import User
from datetime import datetime
from .helpers import BaseApplicationTest, JSONUpdateTestMixin


class TestUsersPut(BaseApplicationTest):
    def test_can_put_a_user(self):
        response = self.client.put(
            '/users',
            data=json.dumps({
                'users': {
                    'email_address': 'joeblogs@email.com',
                    'password': '1234567890',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        print response.get_data()
        assert_equal(response.status_code, 201)
