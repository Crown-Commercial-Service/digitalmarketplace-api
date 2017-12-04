from flask import json
from freezegun import freeze_time
from app import db, encryption
from app.models import User, Supplier, BuyerEmailDomain
from datetime import datetime
import mock
from sqlalchemy.exc import DataError
from tests.bases import BaseApplicationTest, JSONTestMixin, JSONUpdateTestMixin
from tests.helpers import FixtureMixin, load_example_listing


class BaseUserTest(BaseApplicationTest):
    users = None

    def setup(self):
        super(BaseUserTest, self).setup()
        self.users = []

    def _post_user(self, user):
        response = self.client.post(
            '/users',
            data=json.dumps({'users': user}),
            content_type='application/json')

        assert response.status_code == 201
        self.users.append(json.loads(response.get_data())["users"])

    def _return_post_login(self, auth_users=None, status_code=200):
        _auth_users = {
            'emailAddress': 'joeblogs@digital.cabinet-office.gov.uk',
            'password': '1234567890'
        }
        if auth_users is not None and isinstance(auth_users, dict):
            _auth_users.update(auth_users)

        response = self.client.post(
            '/users/auth',
            data=json.dumps({'authUsers': _auth_users}),
            content_type='application/json')
        assert response.status_code == status_code
        return response


class TestUsersAuth(BaseUserTest):
    def create_user(self):
        with self.app.app_context():
            user = {
                'emailAddress': 'joeblogs@digital.cabinet-office.gov.uk',
                'password': '1234567890',
                'role': 'admin',
                'name': 'joe bloggs'
            }
            self._post_user(user)

    def valid_login(self):
        return self._return_post_login()

    def invalid_password(self):
        return self._return_post_login(
            auth_users={'password': 'invalid'},
            status_code=403
        )

    def test_should_validate_credentials(self):
        self.create_user()
        with self.app.app_context():
            response = self.valid_login()

            data = json.loads(response.get_data())['users']
            assert data['emailAddress'] == 'joeblogs@digital.cabinet-office.gov.uk'

    def test_should_validate_mixedcase_credentials(self):
        self.create_user()
        with self.app.app_context():
            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'JOEbloGS@digital.cabinet-office.gov.uk',
                        'password': '1234567890'}}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['emailAddress'] == 'joeblogs@digital.cabinet-office.gov.uk'

    def test_should_return_404_for_no_user(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'joeblogs@digital.cabinet-office.gov.uk',
                        'password': '1234567890'}}),
                content_type='application/json')

            assert response.status_code == 404
            data = json.loads(response.get_data())
            assert data['authorization'] is False

    def test_should_return_403_for_bad_password(self):
        self.create_user()
        with self.app.app_context():
            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'joeblogs@digital.cabinet-office.gov.uk',
                        'password': 'this is not right'}}),
                content_type='application/json')

            assert response.status_code == 403
            data = json.loads(response.get_data())
            assert data['authorization'] is False

    def test_logged_in_at_is_updated_on_successful_login(self):
        self.create_user()
        with self.app.app_context(), freeze_time('2015-06-06'):
            self.valid_login()
            user = User.get_by_email_address('joeblogs@digital.cabinet-office.gov.uk')

            assert user.logged_in_at == datetime(2015, 6, 6)

    def test_logged_in_at_is_not_updated_on_failed_login(self):
        self.create_user()
        with self.app.app_context(), freeze_time('2015-06-06'):
            self.invalid_password()
            user = User.get_by_email_address('joeblogs@digital.cabinet-office.gov.uk')

            assert user.logged_in_at is None

    def test_failed_login_should_increment_failed_login_counter(self):
        self.create_user()
        with self.app.app_context():
            self.invalid_password()
            user = User.get_by_email_address('joeblogs@digital.cabinet-office.gov.uk')

            assert user.failed_login_count == 1

    def test_successful_login_resets_failed_login_counter(self):
        self.create_user()
        with self.app.app_context():
            self.invalid_password()
            self.valid_login()

            user = User.get_by_email_address('joeblogs@digital.cabinet-office.gov.uk')
            assert user.failed_login_count == 0

    def test_user_is_locked_after_too_many_failed_login_attempts(self):
        self.create_user()

        self.app.config['DM_FAILED_LOGIN_LIMIT'] = 1

        with self.app.app_context():
            self.invalid_password()
            user = User.get_by_email_address('joeblogs@digital.cabinet-office.gov.uk')

            assert user.locked is True

    def test_all_login_attempts_fail_for_locked_users(self):
        self.create_user()

        self.app.config['DM_FAILED_LOGIN_LIMIT'] = 1

        with self.app.app_context():
            user = User.get_by_email_address('joeblogs@digital.cabinet-office.gov.uk')

            user.failed_login_count = 1
            db.session.add(user)
            db.session.commit()
            self._return_post_login(status_code=403)


class TestUsersPost(BaseApplicationTest, JSONTestMixin, FixtureMixin):
    method = "post"
    endpoint = "/users"

    def setup(self):
        super(TestUsersPost, self).setup()
        self.setup_default_buyer_domain()

    def test_can_post_a_buyer_user(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@digital.gov.uk',
                    'phoneNumber': '01234 567890',
                    'password': '1234567890',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.get_data())["users"]
        assert data["emailAddress"] == "joeblogs@digital.gov.uk"
        assert data["phoneNumber"] == "01234 567890"

    def test_creating_buyer_user_with_bad_email_domain_fails(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@example.com',
                    'password': '1234567890',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 400
        assert json.loads(response.get_data())['error'] == 'invalid_buyer_domain'

    def test_creating_buyer_user_with_good_email_domain_succeeds(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@digital.gov.uk',
                    'password': '1234567890',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.get_data())['users']
        assert data['active']

    def test_creating_buyer_user_with_no_phone_number_succeeds(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@digital.gov.uk',
                    'phoneNumber': '',
                    'password': '1234567890',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.get_data())['users']
        assert data['active']

    def test_creating_buyer_user_with_bad_phone_number_fails(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@digital.gov.uk',
                    'phoneNumber': '123456',
                    'password': '1234567890',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 400

    def test_creating_buyer_user_with_no_phone_stores_none(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@digital.gov.uk',
                    'phoneNumber': '',
                    'password': '1234567890',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.get_data())['users']
        assert data['phoneNumber'] is None

    def test_can_post_an_admin_user(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@digital.cabinet-office.gov.uk',
                    'password': '1234567890',
                    'role': 'admin',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.get_data())["users"]
        assert data["emailAddress"] == "joeblogs@digital.cabinet-office.gov.uk"

    def test_can_post_an_admin_ccs_category_user(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@crowncommercial.gov.uk',
                    'password': '1234567890',
                    'role': 'admin-ccs-category',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.get_data())["users"]
        assert data["emailAddress"] == "joeblogs@crowncommercial.gov.uk"

    def test_can_post_an_admin_ccs_sourcing_user(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs+sourcing@crowncommercial.gov.uk',
                    'password': '1234567890',
                    'role': 'admin-ccs-sourcing',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.get_data())["users"]
        assert data["emailAddress"] == "joeblogs+sourcing@crowncommercial.gov.uk"

    def test_can_post_an_admin_manager_user(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs+manager@digital.cabinet-office.gov.uk',
                    'password': '1234567890',
                    'role': 'admin-manager',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.get_data())["users"]
        assert data["emailAddress"] == "joeblogs+manager@digital.cabinet-office.gov.uk"

    def test_can_post_an_admin_framework_manager_user(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs+framework+manager@digital.cabinet-office.gov.uk',
                    'password': '1234567890',
                    'role': 'admin-framework-manager',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.get_data())["users"]
        assert data["emailAddress"] == "joeblogs+framework+manager@digital.cabinet-office.gov.uk"

    # The admin-ccs role is no longer in use
    def test_can_not_post_an_admin_ccs_user(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs+admin@crowncommercial.gov.uk',
                    'password': '1234567890',
                    'role': 'admin-ccs',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 400
        error = json.loads(response.get_data())['error']
        assert "'admin-ccs' is not one of" in error

    def test_creating_admin_user_with_bad_email_domain_fails(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@example.com',
                    'password': '1234567890',
                    'role': 'admin',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 400
        assert json.loads(response.get_data())['error'] == 'invalid_admin_domain'

    def test_can_post_a_supplier_user(self, supplier_basic):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@email.com',
                    'password': '1234567890',
                    'supplierId': supplier_basic,
                    'role': 'supplier',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.get_data())["users"]
        assert data["emailAddress"] == "joeblogs@email.com"
        assert data["supplier"]["supplierId"] == supplier_basic

    def test_post_a_user_creates_audit_event(self, supplier_basic):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@email.com',
                    'password': '1234567890',
                    'supplierId': supplier_basic,
                    'role': 'supplier',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 201

        audit_response = self.client.get('/audit-events')
        assert audit_response.status_code == 200
        data = json.loads(audit_response.get_data())

        assert len(data['auditEvents']) == 1
        assert data['auditEvents'][0]['type'] == 'create_user'
        assert data['auditEvents'][0]['data']['supplier_id'] == supplier_basic

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
        assert response.status_code == 400
        assert data == "Invalid supplier id"

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
        assert response.status_code == 400
        assert data == "No supplier id provided for supplier user"

    def test_should_reject_non_supplier_user_with_supplier_id(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@digital.cabinet-office.gov.uk',
                    'password': '1234567890',
                    'role': 'admin',
                    'supplierId': 1,
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        data = json.loads(response.get_data())["error"]
        assert response.status_code == 400
        assert data == "'supplierId' is only valid for users with 'supplier' role, not 'admin'"

    def test_should_reject_user_with_invalid_role(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@email.com',
                    'password': '1234567890',
                    'role': 'shopkeeper',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 400

    def test_can_post_a_user_with_hashed_password(self):
        with self.app.app_context():
            response = self.client.post(
                '/users',
                data=json.dumps({
                    'users': {
                        'hashpw': True,
                        'emailAddress': 'joeblogs@digital.cabinet-office.gov.uk',
                        'password': '1234567890',
                        'role': 'admin',
                        'name': 'joe bloggs'}}),
                content_type='application/json')

            assert response.status_code == 201
            user = User.query.filter(
                User.email_address == 'joeblogs@digital.cabinet-office.gov.uk') \
                .first()
            assert user.password != '1234567890'

    def test_can_post_a_user_without_hashed_password(self):
        with self.app.app_context():
            response = self.client.post(
                '/users',
                data=json.dumps({
                    'users': {
                        'hashpw': False,
                        'emailAddress': 'joeblogs@digital.cabinet-office.gov.uk',
                        'password': '1234567890',
                        'role': 'admin',
                        'name': 'joe bloggs'}}),
                content_type='application/json')

            assert response.status_code == 201
            user = User.query.filter(
                User.email_address == 'joeblogs@digital.cabinet-office.gov.uk') \
                .first()
            assert user.password == '1234567890'

    def test_posting_same_email_twice_is_an_error(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@digital.cabinet-office.gov.uk',
                    'password': '1234567890',
                    'role': 'admin',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 201

        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@digital.cabinet-office.gov.uk',
                    'password': '1234567890',
                    'role': 'admin',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 409

    def test_return_400_for_invalid_user_json(self):
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@gov.uk',
                    'password': '',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.get_data())["error"]
        assert "JSON was not a valid format" in data

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

        assert response.status_code == 400
        data = json.loads(response.get_data())["error"]
        assert "JSON was not a valid format" in data

    @mock.patch('app.db.session.commit')
    def test_create_user_catches_db_errors(self, db_commit):
        db_commit.side_effect = DataError("Unable to commit", orig=None, params={})
        response = self.client.post(
            '/users',
            data=json.dumps({
                'users': {
                    'emailAddress': 'joeblogs@digital.gov.uk',
                    'phoneNumber': '01234 567890',
                    'password': '1234567890',
                    'role': 'buyer',
                    'name': 'joe bloggs'}}),
            content_type='application/json')
        assert response.status_code == 400
        assert "Unable to commit" in json.loads(response.get_data())["error"]


class TestUsersUpdate(BaseApplicationTest, JSONUpdateTestMixin, FixtureMixin):
    method = "post"
    endpoint = "/users/123"

    def setup(self):
        now = datetime.utcnow()
        super(TestUsersUpdate, self).setup()
        with self.app.app_context():
            self.setup_default_buyer_domain()
            user = User(
                id=123,
                email_address="test@digital.gov.uk",
                name="my name",
                password=encryption.hashpw("my long password"),
                active=True,
                role='buyer',
                created_at=now,
                updated_at=now,
                password_changed_at=now
            )
            supplier = Supplier(
                supplier_id=456,
                name="A test supplier"
            )
            supplier_user = User(
                id=456,
                email_address="supplier@digital.gov.uk",
                name="my supplier name",
                password=encryption.hashpw("my long password"),
                active=True,
                role='supplier',
                created_at=now,
                updated_at=now,
                supplier_id=456,
                password_changed_at=now
            )
            db.session.add(supplier)
            db.session.add(user)
            db.session.add(supplier_user)
            db.session.commit()

    def test_can_update_password(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    "updated_by": "a.user",
                    'users': {
                        'password': '1234567890'
                    }}),
                content_type='application/json')

            assert response.status_code == 200

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'test@digital.gov.uk',
                        'password': '1234567890'}}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['emailAddress'] == 'test@digital.gov.uk'

    def test_updating_password_unlocks_user(self):
        self.app.config['DM_FAILED_LOGIN_LIMIT'] = 1

        with self.app.app_context():
            # lock the user using failed auth
            self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'test@digital.gov.uk',
                        'password': 'invalid'}
                }),
                content_type='application/json'
            )

            response = self.client.get(
                '/users/123',
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['locked'] is True
            assert data['failedLoginCount'] == 1

            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    "updated_by": "a.user",
                    'users': {
                        'password': 'newpassword'
                    }}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['locked'] is False

            response = self.client.get('/users/123', content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['locked'] is False
            assert data['failedLoginCount'] == 0

    def test_new_password_is_not_audited(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    "updated_by": "a.user",
                    'users': {
                        'password': 'not-in-my-audit-event'
                    }}),
                content_type='application/json')

            assert response.status_code == 200

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'test@digital.gov.uk',
                        'password': 'not-in-my-audit-event'}}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['emailAddress'] == 'test@digital.gov.uk'

            audit_response = self.client.get('/audit-events')
            assert audit_response.status_code == 200
            data = json.loads(audit_response.get_data())

            assert len(data['auditEvents']) == 1
            assert data['auditEvents'][0]['type'] == 'update_user'
            assert data['auditEvents'][0]['data']['update']['password'] == 'updated'
            assert "not-in-my-audit-event" not in "{}".format(data)

    def test_can_update_active(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    "updated_by": "a.user",
                    'users': {
                        'active': False
                    }}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['active'] is False

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'test@digital.gov.uk',
                        'password': 'my long password'}}),
                content_type='application/json')

            assert response.status_code == 403

    def test_can_unlock_user(self):

        self.app.config['DM_FAILED_LOGIN_LIMIT'] = 1

        with self.app.app_context():

            # lock the user using failed auth
            self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'test@digital.gov.uk',
                        'password': 'invalid'}
                }),
                content_type='application/json'
            )

            response = self.client.get(
                '/users/123',
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['locked'] is True
            assert data['failedLoginCount'] == 1

            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    "updated_by": "a.user",
                    'users': {
                        'locked': False
                    }}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['locked'] is False

            response = self.client.get(
                '/users/123',
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['locked'] is False
            assert data['failedLoginCount'] == 0

    def test_cant_lock_a_user(self):
        with self.app.app_context():

            response = self.client.get(
                '/users/123',
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['locked'] is False
            assert data['failedLoginCount'] == 0

            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    "updated_by": "a.user",
                    'users': {
                        'locked': True
                    }}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['locked'] is False

            response = self.client.get(
                '/users/123',
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['locked'] is False
            assert data['failedLoginCount'] == 0

    def test_can_update_name(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    "updated_by": "a.user",
                    'users': {
                        'name': 'I Just Got Married'
                    }}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['name'] == 'I Just Got Married'

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'test@digital.gov.uk',
                        'password': 'my long password'}}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['name'] == 'I Just Got Married'

    def test_update_creates_audit_event(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    "updated_by": "a.user",
                    'users': {
                        'name': 'I Just Got Married'
                    }}),
                content_type='application/json')

            assert response.status_code == 200

            audit_response = self.client.get('/audit-events')
            assert audit_response.status_code == 200
            data = json.loads(audit_response.get_data())

            assert len(data['auditEvents']) == 1
            assert data['auditEvents'][0]['type'] == 'update_user'
            assert data['auditEvents'][0]['data']['update']['name'] == 'I Just Got Married'

    def test_can_update_role_and_suppler_id(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    "updated_by": "a.user",
                    'users': {
                        'role': 'supplier',
                        'supplierId': 456
                    }}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['role'] == 'supplier'

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'test@digital.gov.uk',
                        'password': 'my long password'}}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['role'] == 'supplier'

    def test_can_update_role_to_buyer_from_supplier(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    "updated_by": "a.user",
                    'users': {
                        'role': 'buyer'
                    }}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['role'] == 'buyer'
            assert data.get('supplierId', None) is None

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'test@digital.gov.uk',
                        'password': 'my long password'}}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['role'] == 'buyer'

    def test_cannot_update_supplier_user_with_invalid_email_address_to_buyer(self):
        response = self.client.post(
            '/users/456',
            data=json.dumps({
                'updated_by': 'a.user',
                'users': {
                    'role': 'buyer',
                    'emailAddress': 'bad@example.com',
                }}),
            content_type='application/json')

        assert response.status_code == 400
        assert json.loads(response.get_data())['error'] == 'invalid_buyer_domain'

    def test_cannot_update_supplier_user_to_buyer_if_email_address_is_already_invalid(self):
        response = self.client.post(
            '/users/456',
            data=json.dumps({
                'updated_by': 'a.user',
                'users': {'emailAddress': 'bad@example.com'},
            }),
            content_type='application/json')

        assert response.status_code == 200

        response = self.client.post(
            '/users/456',
            data=json.dumps({
                'updated_by': 'a.user',
                'users': {'role': 'buyer'},
            }),
            content_type='application/json')

        assert response.status_code == 400
        assert json.loads(response.get_data())['error'] == 'invalid_buyer_domain'

    def test_can_update_role_to_buyer_from_supplier_ignoring_supplier_id(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/456',
                data=json.dumps({
                    "updated_by": "a.user",
                    'users': {
                        'role': 'buyer',
                        'supplierId': 456
                    }}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['role'] == 'buyer'
            assert data.get('supplierId', None) is None

    def test_can_not_update_role_to_invalid_value(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    "updated_by": "a.user",
                    'users': {
                        'role': 'shopkeeper'
                    }}),
                content_type='application/json')

            data = json.loads(response.get_data())["error"]
            assert response.status_code == 400
            assert "Could not update user" in data

    def test_supplier_role_update_requires_supplier_id(self):
        response = self.client.post(
            '/users/123',
            data=json.dumps({
                "updated_by": "a.user",
                'users': {
                    'role': 'supplier'
                }}),
            content_type='application/json')

        data = json.loads(response.get_data())["error"]
        assert response.status_code == 400
        assert "'supplierId' is required for users with 'supplier' role" in data

    def test_can_update_email_address(self):
        with self.app.app_context():
            response = self.client.post(
                '/users/123',
                data=json.dumps({
                    "updated_by": "a.user",
                    'users': {
                        'emailAddress': 'myshinynew@digital.gov.uk'
                    }}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['emailAddress'] == 'myshinynew@digital.gov.uk'

            response = self.client.post(
                '/users/auth',
                data=json.dumps({
                    'authUsers': {
                        'emailAddress': 'myshinynew@digital.gov.uk',
                        'password': 'my long password'}}),
                content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.get_data())['users']
            assert data['emailAddress'] == 'myshinynew@digital.gov.uk'


class TestUsersGet(BaseUserTest, FixtureMixin):
    supplier_id = None

    def setup(self):
        super(TestUsersGet, self).setup()

        # get the last supplier_id returned
        # it turns out we have some logic that doesn't recognise "0" as a supplier_id for users
        self.supplier_id = self.setup_dummy_suppliers(2)[-1]
        with self.app.app_context():
            self.setup_default_buyer_domain()
            self._post_users()

    def _post_users(self):
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

        for user in users:
            self._post_user(user)

    @staticmethod
    def _assert_things_about_users(user_from_api, user_to_compare_to):
        assert user_from_api['emailAddress'] == user_to_compare_to['emailAddress']
        assert user_from_api['name'] == user_to_compare_to['name']
        assert user_from_api['role'] == user_to_compare_to['role']
        assert user_from_api['active'] == user_to_compare_to['active']
        assert user_from_api['locked'] is False
        assert ('password' in user_from_api) is False

    def test_can_get_a_user_by_id(self):
        with self.app.app_context():
            response = self.client.get("/users/{}".format(self.users[0]["id"]))
            assert response.status_code == 200
            data = json.loads(response.get_data())["users"]
            self._assert_things_about_users(data, self.users[0])

    def test_can_get_a_user_by_email(self):
        with self.app.app_context():
            response = self.client.get("/users?email_address=j@examplecompany.biz")
            assert response.status_code == 200
            data = json.loads(response.get_data())["users"][0]
            self._assert_things_about_users(data, self.users[0])

    def test_can_list_users(self):
        with self.app.app_context():
            response = self.client.get("/users")
            assert response.status_code == 200
            data = json.loads(response.get_data())["users"]
            for index, user in enumerate(data):
                self._assert_things_about_users(user, self.users[index])

    def test_can_list_users_by_supplier_id(self):
        with self.app.app_context():
            response = self.client.get("/users?supplier_id={}".format(self.supplier_id))
            assert response.status_code == 200
            data = json.loads(response.get_data())["users"]
            for index, user in enumerate(data):
                self._assert_things_about_users(user, self.users[index])

    def test_returns_404_for_non_int_id(self):
        response = self.client.get("/users/bogus")
        assert response.status_code == 404

    def test_returns_404_for_nonexistent_email_address(self):
        non_existent_email = "jbond@mi6.biz"
        response = self.client.get("/users?email_address={}".format(non_existent_email))
        assert response.status_code == 404

    def test_returns_400_for_non_int_supplier_id(self):
        bad_supplier_id = 'not_an_integer'
        response = self.client.get("/users?supplier_id={}".format(bad_supplier_id))
        assert response.status_code == 400
        assert "Invalid supplier_id: {}".format(bad_supplier_id) in response.get_data(as_text=True)

    def test_returns_404_for_nonexistent_supplier(self):
        non_existent_supplier = self.supplier_id + 1
        response = self.client.get("/users?supplier_id={}".format(non_existent_supplier))
        assert response.status_code == 404
        assert "supplier_id '{}' not found".format(non_existent_supplier) in response.get_data(as_text=True)

    def test_only_buyers_returned_with_role_param_set_to_buyer(self):
        self._post_user({
            "emailAddress": "Chris@digital.gov.uk",
            "name": "Chris",
            "role": "buyer",
            "password": "minimum10characterpassword"
        })

        response = self.client.get('/users?role=buyer')
        data = json.loads(response.get_data())
        buyer = data['users'][0]

        assert response.status_code == 200
        assert len(data['users']) == 1
        assert buyer['name'] == 'Chris'

    def test_list_users_by_admin_role(self):
        self._post_user({
            "emailAddress": "admin@digital.cabinet-office.gov.uk",
            "name": "Admin",
            "role": "admin",
            "password": "minimum10characterpassword"
        })

        response = self.client.get("/users?role=admin")
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['users']) == 1
        assert data['users'][0]['name'] == 'Admin'

    def test_400_returned_if_role_param_is_not_valid(self):
        response = self.client.get('/users?role=incorrect')
        data = response.get_data(as_text=True)

        assert response.status_code == 400
        assert "Invalid user role: incorrect" in data


class TestUsersExport(BaseUserTest, FixtureMixin):
    framework_slug = None
    updater_json = None

    def setup(self):
        super(TestUsersExport, self).setup()
        with self.app.app_context():
            self.setup_default_buyer_domain()
            self.framework_slug = 'digital-outcomes-and-specialists'
            self.set_framework_status(self.framework_slug, 'open')
            self.updater_json = {'updated_by': 'Paul'}

    def _post_users(self):
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

        for user in users:
            self._post_user(user)

    def _register_supplier_with_framework(self):
        response = self.client.put(
            '/suppliers/{}/frameworks/{}'.format(self.supplier_id, self.framework_slug),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert response.status_code == 201

    def _put_declaration(self, status):
        data = {'declaration': {'status': status}}
        data.update(self.updater_json)

        response = self.client.put(
            '/suppliers/{}/frameworks/{}/declaration'.format(self.supplier_id, self.framework_slug),
            data=json.dumps(data),
            content_type='application/json')

        assert response.status_code == 201

    def _put_variation_agreement(self):
        data = {"agreedVariations": {"agreedUserId": self.users[0].get("id")}}
        data.update(self.updater_json)

        response = self.client.put(
            '/suppliers/{}/frameworks/{}/variation/1'.format(self.supplier_id, self.framework_slug),
            data=json.dumps(data),
            content_type='application/json')

        assert response.status_code == 200

    def _put_complete_declaration(self):
        self._put_declaration(status='complete')

    def _put_incomplete_declaration(self):
        self._put_declaration(status='started')

    def _post_complete_draft_service(self):
        payload = load_example_listing("DOS-digital-specialist")

        self.draft_json = {'services': payload}
        self.draft_json['services']['supplierId'] = self.supplier_id
        self.draft_json['services']['frameworkSlug'] = self.framework_slug
        self.draft_json.update(self.updater_json)

        response = self.client.post(
            '/draft-services',
            data=json.dumps(self.draft_json),
            content_type='application/json')

        assert response.status_code == 201

        draft_id = json.loads(response.get_data())['services']['id']
        complete = self.client.post(
            '/draft-services/{}/complete'.format(draft_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert complete.status_code == 200

    def _post_framework_interest(self, data):
        data.update(self.updater_json)
        response = self.client.post(
            '/suppliers/{}/frameworks/{}'.format(self.supplier_id, self.framework_slug),
            data=json.dumps(data),
            content_type='application/json')

        assert response.status_code == 200

    def _create_and_sign_framework_agreement(self):
        response = self.client.post(
            '/agreements',
            data=json.dumps(
                {
                    'updated_by': 'interested@example.com',
                    'agreement': {
                        'supplierId': self.supplier_id,
                        'frameworkSlug': self.framework_slug
                    },
                }),
            content_type='application/json')
        agreement_id = json.loads(response.get_data(as_text=True))['agreement']['id']
        self.client.post(
            "/agreements/{}/sign".format(agreement_id),
            data=json.dumps({'updated_by': 'interested@example.com'}),
            content_type='application/json'
        )

    def _post_result(self, result):
        data = {'frameworkInterest': {'onFramework': result}, 'updated_by': 'Paul'}
        data.update(self.updater_json)
        response = self.client.post(
            '/suppliers/{}/frameworks/{}'.format(self.supplier_id, self.framework_slug),
            data=json.dumps(data),
            content_type='application/json')
        assert response.status_code == 200

    def _set_framework_status(self, status='pending'):
        with self.app.app_context():
            self.set_framework_status(self.framework_slug, status)

    def _set_framework_variation(self):
        with self.app.app_context():
            self.set_framework_variation(self.framework_slug)

    def _return_users_export(self):
        response = self.client.get('/users/export/{}'.format(self.framework_slug))
        assert response.status_code == 200
        return response

    def _return_users_export_after_setting_framework_status(self, status='pending'):
        self._set_framework_status(status)
        return self._return_users_export()

    def _setup(self, post_supplier=True, post_users=True, register_supplier_with_framework=True):
        if post_supplier:
            # set the supplier_id to the id of the last supplier created
            self.supplier_id = self.setup_dummy_suppliers(2)[-1]
        if post_users:
            self._post_users()
        if register_supplier_with_framework:
            self._register_supplier_with_framework()

    def _assert_things_about_export_response(self, row, parameters=None):
        _parameters = {
            'application_result': 'no result',
            'application_status': 'no_application',
            'declaration_status': 'unstarted',
            'framework_agreement': False,
        }

        if parameters is not None and isinstance(parameters, dict):
            _parameters.update(parameters)

        assert row['email address'] in [user['emailAddress'] for user in self.users]
        assert row['user_name'] in [user['name'] for user in self.users]
        assert row['supplier_id'] == self.supplier_id
        assert row['application_result'] == _parameters['application_result']
        assert row['application_status'] == _parameters['application_status']
        assert row['declaration_status'] == _parameters['declaration_status']
        assert row['framework_agreement'] == _parameters['framework_agreement']

    ############################################################################################

    # Test no suppliers
    def test_get_response_when_no_suppliers(self):
        data = json.loads(self._return_users_export_after_setting_framework_status().get_data())["users"]
        assert data == []

    # Test one supplier with no users
    def test_get_response_when_no_users(self):
        self._setup(post_users=False, register_supplier_with_framework=False)
        data = json.loads(self._return_users_export_after_setting_framework_status().get_data())["users"]
        assert data == []

    # Test one supplier not registered on the framework
    def test_get_response_when_not_registered_with_framework(self):
        self._setup(register_supplier_with_framework=False)
        data = json.loads(self._return_users_export_after_setting_framework_status().get_data())["users"]
        assert data == []

    # Test users for supplier with unstarted declaration no drafts
    def test_response_unstarted_declaration_no_drafts(self):
        self._setup()
        data = json.loads(self._return_users_export_after_setting_framework_status().get_data())["users"]
        assert len(data) == len(self.users)
        for datum in data:
            self._assert_things_about_export_response(datum)

    # Test users for supplier with unstarted declaration one draft
    def test_response_unstarted_declaration_one_draft(self):
        self._setup()
        self._post_complete_draft_service()
        data = json.loads(self._return_users_export_after_setting_framework_status().get_data())["users"]
        assert len(data) == len(self.users)
        for datum in data:
            self._assert_things_about_export_response(datum)

    # Test users for supplier with started declaration one draft
    def test_response_started_declaration_one_draft(self):
        self._setup()
        self._put_incomplete_declaration()
        self._post_complete_draft_service()
        data = json.loads(self._return_users_export_after_setting_framework_status().get_data())["users"]
        assert len(data) == len(self.users)
        for datum in data:
            self._assert_things_about_export_response(datum, parameters={'declaration_status': 'started'})

    # Test users for supplier with completed declaration no drafts
    def test_response_complete_declaration_no_drafts(self):
        self._setup()
        self._put_complete_declaration()
        data = json.loads(self._return_users_export_after_setting_framework_status().get_data())["users"]
        assert len(data) == len(self.users)
        for datum in data:
            self._assert_things_about_export_response(datum, parameters={'declaration_status': 'complete'})

    # Test users for supplier with completed declaration one draft
    def test_response_complete_declaration_one_draft(self):
        self._setup()
        self._put_complete_declaration()
        self._post_complete_draft_service()
        data = json.loads(self._return_users_export_after_setting_framework_status().get_data())["users"]
        assert len(data) == len(self.users)
        for datum in data:
            self._assert_things_about_export_response(datum, parameters={
                'declaration_status': 'complete',
                'application_status': 'application'
            })

    # Test users for supplier with completed declaration one draft but framework still open
    def test_response_complete_declaration_one_draft_while_framework_still_open(self):
        self._setup()
        self._put_complete_declaration()
        self._post_complete_draft_service()
        data = json.loads(self._return_users_export_after_setting_framework_status(status='open').get_data())["users"]
        assert len(data) == len(self.users)
        for datum in data:
            self._assert_things_about_export_response(datum, parameters={
                'declaration_status': 'complete',
                'application_status': 'application',
                'application_result': '',
                'framework_agreement': ''
            })

    def test_response_awarded_on_framework_and_submitted_framework_agreement(self):
        self._setup()
        self._put_complete_declaration()
        self._post_complete_draft_service()
        self._post_result(True)
        self._create_and_sign_framework_agreement()
        data = json.loads(self._return_users_export_after_setting_framework_status().get_data())["users"]
        assert len(data) == len(self.users)
        for datum in data:
            self._assert_things_about_export_response(datum, parameters={
                'declaration_status': 'complete',
                'application_status': 'application',
                'framework_agreement': True,
                'application_result': 'pass'
            })

    def test_response_not_awarded_on_framework(self):
        self._setup()
        self._put_complete_declaration()
        self._post_complete_draft_service()
        self._post_result(False)
        data = json.loads(self._return_users_export_after_setting_framework_status().get_data())["users"]
        assert len(data) == len(self.users)
        for datum in data:
            self._assert_things_about_export_response(datum, parameters={
                'declaration_status': 'complete',
                'application_status': 'application',
                'framework_agreement': False,
                'application_result': 'fail'
            })

    def test_response_does_not_include_disabled_users(self):
        self._setup()
        self._post_user({
            "emailAddress": "disabled-user@example.com",
            "name": "Disabled User",
            "password": "minimum10characterpassword",
            "role": "supplier",
            "supplierId": self.supplier_id
        })
        response = self.client.post(
            '/users/{}'.format(self.users[-1]['id']),
            data=json.dumps({
                "users": {"active": False},
                "updated_by": "test"
            }),
            content_type='application/json')
        assert response.status_code == 200

        data = json.loads(self._return_users_export_after_setting_framework_status().get_data())["users"]
        assert len(data) == len(self.users) - 1

    # Test 400 if bad framework name
    def test_400_response_if_bad_framework_name(self):
        self._setup()
        response = self.client.get('/users/export/{}'.format('cyber-outcomes-and-cyber-specialists'))
        assert response.status_code == 400

    # Test 400 if bad framework status
    def test_400_response_if_framework_is_coming(self):
        self._setup()
        self._set_framework_status('coming')
        response = self.client.get('/users/export/{}'.format(self.framework_slug))
        assert response.status_code == 400

    def test_response_agreed_contract_variation(self):
        self._setup()
        self._put_complete_declaration()
        self._post_complete_draft_service()
        self._post_result(True)
        self._create_and_sign_framework_agreement()
        self._set_framework_variation()
        self._put_variation_agreement()
        data = json.loads(self._return_users_export_after_setting_framework_status(status='live').get_data())["users"]
        assert len(data) == len(self.users)
        for datum in data:
            self._assert_things_about_export_response(datum, parameters={
                'declaration_status': 'complete',
                'application_status': 'application',
                'application_result': 'pass',
                'framework_agreement': True,
                'agreed_variations': '1'
            })


class TestUsersEmailCheck(BaseUserTest):
    def test_valid_email_is_ok_if_domain_found_in_database(self):
        with self.app.app_context():
            # Create a domain that isn't in the buyer-email-domains.txt file
            db.session.add(BuyerEmailDomain(domain_name="bananas.org"))
            db.session.commit()

        response = self.client.get('/users/check-buyer-email', query_string={'email_address': 'buyer@bananas.org'})
        assert response.status_code == 200
        assert json.loads(response.get_data())['valid'] is True

    def test_invalid_email_is_not_ok(self):
        response = self.client.get('/users/check-buyer-email', query_string={'email_address': 'someone@notgov.uk'})
        assert response.status_code == 200
        assert json.loads(response.get_data())['valid'] is False

    def test_email_address_is_required(self):
        response = self.client.get('/users/check-buyer-email')
        assert response.status_code == 400


class TestAdminEmailCheck(BaseUserTest):

    def setup(self):
        super(TestAdminEmailCheck, self).setup()
        self.app.config['DM_ALLOWED_ADMIN_DOMAINS'] = ['bananas.org']

    def test_email_address_is_required(self):
        response = self.client.get('/users/valid-admin-email')
        assert response.status_code == 400

    def test_invalid_email_is_not_ok(self):
        response = self.client.get(
            '/users/valid-admin-email',
            query_string={'email_address': 'buyer@i-dislike-bananas.org'}
        )
        assert response.status_code == 200
        assert json.loads(response.get_data())['valid'] is False

    def test_valid_email_is_ok_if_admin_domain_found_in_config(self):
        response = self.client.get('/users/valid-admin-email', query_string={'email_address': 'buyer@bananas.org'})
        assert response.status_code == 200
        assert json.loads(response.get_data())['valid'] is True

    def test_returns_invalid_if_no_config_value_set(self):
        self.app.config.pop('DM_ALLOWED_ADMIN_DOMAINS')

        response = self.client.get('/users/valid-admin-email', query_string={'email_address': 'buyer@bananas.org'})
        assert response.status_code == 200
        assert json.loads(response.get_data())['valid'] is False
