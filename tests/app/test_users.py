from flask import json
from freezegun import freeze_time
from nose.tools import assert_equal, assert_not_equal, assert_in
from app import db, encryption
from app.models import User, Supplier
from datetime import datetime
from .helpers import BaseApplicationTest, JSONUpdateTestMixin
from dmutils.formats import DATETIME_FORMAT


class TestUsersAuth(BaseApplicationTest):
    def create_user(self):
        with self.app.app_context():
            response = self.client.post(
                '/users',
                data=json.dumps({
                    'users': {
                        'emailAddress': 'joeblogs@email.com',
                        'password': '1234567890',
                        'role': 'buyer',
                        'name': 'joe bloggs'}}),
                content_type='application/json')
            assert_equal(response.status_code, 201)

    def valid_login(self):
        return self.client.post(
            '/users/auth',
            data=json.dumps({
                'authUsers': {
                    'emailAddress': 'joeblogs@email.com',
                    'password': '1234567890'}}),
            content_type='application/json')

    def invalid_password(self):
        return self.client.post(
            '/users/auth',
            data=json.dumps({
                'authUsers': {
                    'emailAddress': 'joeblogs@email.com',
                    'password': 'invalid'}}),
            content_type='application/json')

    def test_should_validate_credentials(self):
        self.create_user()
        with self.app.app_context():
            response = self.valid_login()

            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())['users']
            assert_equal(data['emailAddress'], 'joeblogs@email.com')

    def test_should_validate_mixedcase_credentials(self):
        self.create_user()
        with self.app.app_context():
            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'JOEbloGS@email.com',
                        'password': '1234567890'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())['users']
            assert_equal(data['emailAddress'], 'joeblogs@email.com')

    def test_should_return_404_for_no_user(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'joeblogs@email.com',
                        'password': '1234567890'}}),
                content_type='application/json')

            assert_equal(response.status_code, 404)
            data = json.loads(response.get_data())
            assert_equal(data['authorization'], False)

    def test_should_return_403_for_bad_password(self):
        self.create_user()
        with self.app.app_context():
            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'joeblogs@email.com',
                        'password': 'this is not right'}}),
                content_type='application/json')

            assert_equal(response.status_code, 403)
            data = json.loads(response.get_data())
            assert_equal(data['authorization'], False)

    def test_logged_in_at_is_updated_on_successful_login(self):
        self.create_user()
        with self.app.app_context(), freeze_time('2015-06-06'):
            self.valid_login()
            user = User.get_by_email_address('joeblogs@email.com')

            assert_equal(user.logged_in_at, datetime(2015, 6, 6))

    def test_logged_in_at_is_not_updated_on_failed_login(self):
        self.create_user()
        with self.app.app_context(), freeze_time('2015-06-06'):
            self.invalid_password()
            user = User.get_by_email_address('joeblogs@email.com')

            assert_equal(user.logged_in_at, None)

    def test_failed_login_should_increment_failed_login_counter(self):
        self.create_user()
        with self.app.app_context():
            self.invalid_password()
            user = User.get_by_email_address('joeblogs@email.com')

            assert_equal(user.failed_login_count, 1)

    def test_successful_login_resets_failed_login_counter(self):
        self.create_user()
        with self.app.app_context():
            self.invalid_password()
            self.valid_login()

            user = User.get_by_email_address('joeblogs@email.com')
            assert_equal(user.failed_login_count, 0)

    def test_user_is_locked_after_too_many_failed_login_attempts(self):
        self.create_user()

        self.app.config['DM_FAILED_LOGIN_LIMIT'] = 1

        with self.app.app_context():
            self.invalid_password()
            user = User.get_by_email_address('joeblogs@email.com')

            assert_equal(user.locked, True)

    def test_all_login_attempts_fail_for_locked_users(self):
        self.create_user()

        self.app.config['DM_FAILED_LOGIN_LIMIT'] = 1

        with self.app.app_context():
            user = User.get_by_email_address('joeblogs@email.com')

            user.failed_login_count = 1
            db.session.add(user)
            db.session.commit()
            response = self.valid_login()

            assert_equal(response.status_code, 403)


class TestUsersPost(BaseApplicationTest, JSONUpdateTestMixin):
    method = "post"
    endpoint = "/users"

    def test_can_post_a_buyer_user(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@email.com',
                    'password': '1234567890',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 201)
        data = json.loads(response.get_data())["users"]
        assert_equal(data["emailAddress"], "joeblogs@email.com")

    def test_can_post_an_admin_user(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@email.com',
                    'password': '1234567890',
                    'role': 'admin',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 201)
        data = json.loads(response.get_data())["users"]
        assert_equal(data["emailAddress"], "joeblogs@email.com")

    def test_can_post_a_supplier_user(self):
        with self.app.app_context():
            db.session.add(
                Supplier(supplier_id=1, name=u"Supplier 1")
            )
            db.session.commit()

        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@email.com',
                    'password': '1234567890',
                    'supplierId': 1,
                    'role': 'supplier',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 201)
        data = json.loads(response.get_data())["users"]
        assert_equal(data["emailAddress"], "joeblogs@email.com")
        assert_equal(data["supplier"]["name"], "Supplier 1")
        assert_equal(data["supplier"]["supplierId"], 1)

    def test_post_a_user_creates_audit_event(self):
        with self.app.app_context():
            db.session.add(
                Supplier(supplier_id=1, name=u"Supplier 1")
            )
            db.session.commit()

        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@email.com',
                    'password': '1234567890',
                    'supplierId': 1,
                    'role': 'supplier',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 201)

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())

        assert_equal(len(data['auditEvents']), 1)
        assert_equal(data['auditEvents'][0]['type'], 'create_user')
        assert_equal(data['auditEvents'][0]['data']['supplier_id'], 1)

    def test_should_reject_a_supplier_user_with_invalid_supplier_id(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@email.com',
                    'password': '1234567890',
                    'supplierId': 999,
                    'role': 'supplier',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        data = json.loads(response.get_data())["error"]
        assert_equal(response.status_code, 400)
        assert_equal(data, "Invalid supplier id")

    def test_should_reject_a_supplier_user_with_no_supplier_id(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@email.com',
                    'password': '1234567890',
                    'role': 'supplier',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        data = json.loads(response.get_data())["error"]
        assert_equal(response.status_code, 400)
        assert_equal(data, "No supplier id provided for supplier user")

    def test_can_post_a_user_with_hashed_password(self):
        with self.app.app_context():
            response = self.client.post(
                '/users',
                data=json.dumps({
                    'users': {
                        'hashpw': True,
                        'emailAddress': 'joeblogs@email.com',
                        'password': '1234567890',
                        'role': 'buyer',
                        'name': 'joe bloggs'}}),
                content_type='application/json')

            assert_equal(response.status_code, 201)
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
                        'emailAddress': 'joeblogs@email.com',
                        'password': '1234567890',
                        'role': 'buyer',
                        'name': 'joe bloggs'}}),
                content_type='application/json')

            assert_equal(response.status_code, 201)
            user = User.query.filter(
                User.email_address == 'joeblogs@email.com') \
                .first()
            assert_equal(user.password, '1234567890')

    def test_posting_same_email_twice_is_an_error(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@email.com',
                    'password': '1234567890',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 201)

        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@email.com',
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
                    'emailAddress': 'joeblogs@email.com',
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
                    'emailAddress': 'joeblogs@email.com',
                    'password': '0000000000',
                    'role': 'invalid',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        data = json.loads(response.get_data())["error"]
        assert_equal(data, "JSON was not a valid format")


class TestUsersUpdate(BaseApplicationTest):
    def setup(self):
        now = datetime.utcnow()
        super(TestUsersUpdate, self).setup()
        with self.app.app_context():
            user = User(
                id=123,
                email_address="test@test.com",
                name="my name",
                password=encryption.hashpw("my long password"),
                active=True,
                role='buyer',
                created_at=now,
                updated_at=now,
                password_changed_at=now
            )
            db.session.add(user)

            supplier = Supplier(
                supplier_id=456,
                name="A test supplier"
            )
            db.session.add(supplier)
            db.session.commit()

    def test_can_update_password(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    'users': {
                        'password': '1234567890'
                    }}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'test@test.com',
                        'password': '1234567890'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())['users']
            assert_equal(data['emailAddress'], 'test@test.com')

    def test_can_update_active(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    'users': {
                        'active': False
                    }}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'test@test.com',
                        'password': 'my long password'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())['users']
            assert_equal(data['active'], False)

    def test_can_not_update_locked(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    'users': {
                        'locked': True
                    }}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.get(
                '/users/123',
                content_type='application/json')

            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())['users']
            assert_equal(data['locked'], False)

    def test_can_update_name(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    'users': {
                        'name': 'I Just Got Married'
                    }}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'test@test.com',
                        'password': 'my long password'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())['users']
            assert_equal(data['name'], 'I Just Got Married')

    def test_update_creates_audit_event(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    'users': {
                        'name': 'I Just Got Married'
                    }}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            audit_response = self.client.get('/audit-events')
            assert_equal(audit_response.status_code, 200)
            data = json.loads(audit_response.get_data())

            assert_equal(len(data['auditEvents']), 1)
            assert_equal(data['auditEvents'][0]['type'], 'update_user')
            assert_equal(
                data['auditEvents'][0]['data']['update']['name'],
                'I Just Got Married'
            )

    def test_can_update_role_and_suppler_id(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    'users': {
                        'role': 'supplier',
                        'supplierId': 456
                    }}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'test@test.com',
                        'password': 'my long password'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())['users']
            assert_equal(data['role'], 'supplier')

    def test_can_not_update_role_to_invalid_value(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    'users': {
                        'role': 'shopkeeper'
                    }}),
                content_type='application/json')

            data = json.loads(response.get_data())["error"]
            assert_equal(response.status_code, 400)
            assert_in("Could not update user", data)

    def test_can_update_email_address(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    'users': {
                        'emailAddress': 'myshinynew@email.address'
                    }}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'myshinynew@email.address',
                        'password': 'my long password'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())['users']
            assert_equal(data['emailAddress'], 'myshinynew@email.address')


class TestUsersGet(BaseApplicationTest):
    def setup(self):
        super(TestUsersGet, self).setup()
        with self.app.app_context():
            payload = self.load_example_listing("Supplier")
            self.supplier = payload
            self.supplier_id = payload['id']

            response = self.client.put(
                '/suppliers/{}'.format(self.supplier_id),
                data=json.dumps({
                    'suppliers': self.supplier
                }),
                content_type='application/json')
            assert_equal(response.status_code, 201)

            users = [
                {
                    "emailAddress": "j@examplecompany.biz",
                    "name": "John Example",
                    "password": "minimum10characterpassword",
                    "role": "supplier",
                    "supplierId": self.supplier_id
                },
                {
                    "emailAddress": "don@don.com",
                    "name": "Don",
                    "password": "minimum10characterpassword",
                    "role": "supplier",
                    "supplierId": self.supplier_id
                }
            ]
            self.users = []

            for user in users:
                response = self.client.post(
                    '/users',
                    data=json.dumps({
                        'users': user
                    }),
                    content_type='application/json')

                assert_equal(response.status_code, 201)
                self.users.append(json.loads(response.get_data())["users"])

    def test_can_get_a_user_by_id(self):
        with self.app.app_context():
            response = self.client.get("/users/{}".format(self.users[0]["id"]))
            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())["users"]
            assert_equal(data['emailAddress'], self.users[0]['emailAddress'])
            assert_equal(data['name'], self.users[0]['name'])
            assert_equal(data['role'], self.users[0]['role'])
            assert_equal(data['active'], True)
            assert_equal(data['locked'], False)
            assert_equal('password' in data, False)

    def test_can_get_a_user_by_email(self):
        with self.app.app_context():
            response = self.client.get("/users?email_address=j@examplecompany.biz")
            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())["users"][0]
            assert_equal(data['emailAddress'], self.users[0]['emailAddress'])
            assert_equal(data['name'], self.users[0]['name'])
            assert_equal(data['role'], self.users[0]['role'])
            assert_equal(data['active'], True)
            assert_equal(data['locked'], False)
            assert_equal('password' in data, False)

    def test_can_list_users(self):
        with self.app.app_context():
            response = self.client.get("/users")
            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())["users"]
            for index, user in enumerate(data):
                assert_equal(user['emailAddress'], self.users[index]["emailAddress"])
                assert_equal(user['name'], self.users[index]["name"])
                assert_equal(user['role'], self.users[index]["role"])
                assert_equal(user['active'], True)
                assert_equal(user['locked'], False)
                assert_equal('password' in user, False)

    def test_can_list_users_by_supplier_id(self):
        with self.app.app_context():
            response = self.client.get("/users?supplier_id={}".format(self.supplier_id))
            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())["users"]
            for index, user in enumerate(data):
                assert_equal(user['emailAddress'], self.users[index]["emailAddress"])
                assert_equal(user['name'], self.users[index]["name"])
                assert_equal(user['role'], self.users[index]["role"])
                assert_equal(user['active'], True)
                assert_equal(user['locked'], False)
                assert_equal('password' in user, False)

    def test_returns_404_for_non_int_id(self):
        response = self.client.get("/users/bogus")
        assert_equal(response.status_code, 404)

    def test_returns_404_for_nonexistent_email_address(self):
        non_existent_email = "jbond@mi6.biz"
        response = self.client.get("/users?email_address={}".format(non_existent_email))
        data = json.loads(response.get_data())["error"]
        assert_equal(response.status_code, 404)
        assert_equal(
            data,
            "No user with email_address 'jbond@mi6.biz'".format(non_existent_email)
        )

    def test_returns_400_for_non_int_supplier_id(self):
        bad_supplier_id = 'not_an_integer'
        response = self.client.get("/users?supplier_id={}".format(bad_supplier_id))
        assert_equal(response.status_code, 400)
        assert_in(
            "Invalid supplier_id: {}".format(bad_supplier_id),
            response.get_data(as_text=True)
        )

    def test_returns_404_for_nonexistent_supplier(self):
        non_existent_supplier = self.supplier_id + 1
        response = self.client.get("/users?supplier_id={}".format(non_existent_supplier))
        assert_equal(response.status_code, 404)
        assert_in(
            "supplier_id '{}' not found".format(non_existent_supplier),
            response.get_data(as_text=True)
        )
