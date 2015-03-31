from flask import json
from nose.tools import assert_equal
from app import db
from app.models import User
from datetime import datetime
from .helpers import BaseApplicationTest, JSONUpdateTestMixin


class TestUsersPut(BaseApplicationTest, JSONUpdateTestMixin):
    method = "put"
    endpoint = "/users"

    def test_can_put_a_user(self):
        response = self.client.put(
            '/users',
            data=json.dumps({
                'users': {
                    'email_address': 'joeblogs@email.com',
                    'password': '1234567890',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 201)

    def test_can_replace_a_user(self):
        response = self.client.put(
            '/users',
            data=json.dumps({
                'users': {
                    'email_address': 'joeblogs@email.com',
                    'password': '1234567890',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 201)

        response = self.client.put(
            '/users',
            data=json.dumps({
                'users': {
                    'email_address': 'joeblogs@email.com',
                    'password': '1234567890',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 204)

    def test_return_400_for_invalid_user_json(self):
        response = self.client.put(
            '/users',
            data=json.dumps({
                'users': {
                    'email_address': 'joeblogs@email.com',
                    'password': '',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)


class TestUsersGet(BaseApplicationTest):
    def setup(self):
        now = datetime.now()
        super(TestUsersGet, self).setup()
        with self.app.app_context():
            user = User(
                id=123,
                email_address="test@test.com",
                name="my name",
                password="my long password",
                active=True,
                locked=False,
                created_at=now,
                updated_at=now,
                password_changed_at=now
            )
            db.session.add(user)

    def test_can_get_a_user(self):
        response = self.client.get("/users/123")
        data = json.loads(response.get_data())["users"]
        assert_equal(data['email_address'], "test@test.com")
        assert_equal(data['name'], "my name")
        assert_equal(data['active'], True)
        assert_equal(data['locked'], False)
        assert_equal('password' in data, False)
        assert_equal(response.status_code, 200)

    def test_returns_404_for_non_int_id(self):
        response = self.client.get("/users/bogus")
        assert_equal(response.status_code, 404)