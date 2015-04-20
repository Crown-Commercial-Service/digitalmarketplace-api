from flask import json
from nose.tools import assert_equal, assert_not_equal

from app import db
from app.models import User
from datetime import datetime
from .helpers import BaseApplicationTest, JSONUpdateTestMixin


class TestUsersAuth(BaseApplicationTest):
    def test_should_validate_credentials(self):
        with self.app.app_context():
            response = self.client.post(
                '/users',
                data=json.dumps({
                    'users': {
                        'email_address': 'joeblogs@email.com',
                        'password': '1234567890',
                        'role': 'buyer',
                        'name': 'joe bloggs'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'auth_users': {
                        'email_address': 'joeblogs@email.com',
                        'password': '1234567890'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())['users']
            assert_equal(data['email_address'], 'joeblogs@email.com')

    def test_should_validate_mixedcase_credentials(self):
        with self.app.app_context():
            response = self.client.post(
                '/users',
                data=json.dumps({
                    'users': {
                        'email_address': 'joEblogS@EMAIL.com',
                        'password': '1234567890',
                        'role': 'buyer',
                        'name': 'joe bloggs'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'auth_users': {
                        'email_address': 'JOEbloGS@email.com',
                        'password': '1234567890'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())['users']
            assert_equal(data['email_address'], 'joeblogs@email.com')

    def test_should_return_404_for_no_user(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'auth_users': {
                        'email_address': 'joeblogs@email.com',
                        'password': '1234567890'}}),
                content_type='application/json')

            assert_equal(response.status_code, 404)
            data = json.loads(response.get_data())
            assert_equal(data['authorization'], False)

    def test_should_return_403_for_bad_password(self):
        with self.app.app_context():
            response = self.client.post(
                '/users',
                data=json.dumps({
                    'users': {
                        'email_address': 'joeblogs@email.com',
                        'password': '1234567890',
                        'role': 'buyer',
                        'name': 'joe bloggs'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'auth_users': {
                        'email_address': 'joeblogs@email.com',
                        'password': 'this is not right'}}),
                content_type='application/json')

            assert_equal(response.status_code, 403)
            data = json.loads(response.get_data())
            assert_equal(data['authorization'], False)


class TestUsersPost(BaseApplicationTest, JSONUpdateTestMixin):
    method = "post"
    endpoint = "/users"

    def test_can_post_a_user(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'email_address': 'joeblogs@email.com',
                    'password': '1234567890',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 200)
        data = json.loads(response.get_data())["users"]
        assert_equal(data["email_address"], "joeblogs@email.com")

    def test_can_post_an_admin_user(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'email_address': 'joeblogs@email.com',
                    'password': '1234567890',
                    'role': 'admin',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 200)
        data = json.loads(response.get_data())["users"]
        assert_equal(data["email_address"], "joeblogs@email.com")

    def test_can_post_a_supplier_user(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'email_address': 'joeblogs@email.com',
                    'password': '1234567890',
                    'role': 'supplier',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 200)
        data = json.loads(response.get_data())["users"]
        assert_equal(data["email_address"], "joeblogs@email.com")

    def test_can_post_a_user_with_hashed_password(self):
        with self.app.app_context():
            response = self.client.post(
                '/users',
                data=json.dumps({
                    'users': {
                        'hashpw': True,
                        'email_address': 'joeblogs@email.com',
                        'password': '1234567890',
                        'role': 'buyer',
                        'name': 'joe bloggs'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)
            user = User.query.filter(
                User.email_address == 'joeblogs@email.com') \
                .first()
            assert_not_equal(user.password, '1234567890')

    def test_can_post_a_user_without_hashed_password(self):
        with self.app.app_context():
            response = self.client.post(
                '/users',
                data=json.dumps({
                    'users': {
                        'hashpw': False,
                        'email_address': 'joeblogs@email.com',
                        'password': '1234567890',
                        'role': 'buyer',
                        'name': 'joe bloggs'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)
            user = User.query.filter(
                User.email_address == 'joeblogs@email.com') \
                .first()
            assert_equal(user.password, '1234567890')

    def test_posting_same_email_twice_is_an_error(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'email_address': 'joeblogs@email.com',
                    'password': '1234567890',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 200)

        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'email_address': 'joeblogs@email.com',
                    'password': '1234567890',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 409)

    def test_return_400_for_invalid_user_json(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'email_address': 'joeblogs@email.com',
                    'password': '',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        data = json.loads(response.get_data())["error"]
        assert_equal(data, "JSON was not a valid format")

    def test_return_400_for_invalid_user_role(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'email_address': 'joeblogs@email.com',
                    'password': '0000000000',
                    'role': 'invalid',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        data = json.loads(response.get_data())["error"]
        assert_equal(data, "JSON was not a valid format")


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
                role='buyer',
                created_at=now,
                updated_at=now,
                password_changed_at=now
            )
            db.session.add(user)
            db.session.commit()

    def test_can_get_a_user(self):
        response = self.client.get("/users/123")
        data = json.loads(response.get_data())["users"]
        assert_equal(data['email_address'], "test@test.com")
        assert_equal(data['name'], "my name")
        assert_equal(data['role'], "buyer")
        assert_equal(data['active'], True)
        assert_equal(data['locked'], False)
        assert_equal('password' in data, False)
        assert_equal(response.status_code, 200)

    def test_returns_404_for_non_int_id(self):
        response = self.client.get("/users/bogus")
        assert_equal(response.status_code, 404)
