from __future__ import absolute_import

import os
import json
from datetime import datetime

from nose.tools import assert_equal, assert_in

from app import create_app, db
from app.models import Service, Supplier, Framework


TEST_SUPPLIERS_COUNT = 3


class WSGIApplicationWithEnvironment(object):
    def __init__(self, app, **kwargs):
        self.app = app
        self.kwargs = kwargs

    def __call__(self, environ, start_response):
        for key, value in self.kwargs.items():
            environ[key] = value
        return self.app(environ, start_response)


class BaseApplicationTest(object):
    lots = {
        "iaas": "G6-IaaS.json",
        "saas": "G6-SaaS.json",
        "paas": "G6-PaaS.json",
        "scs": "G6-SCS.json"
    }

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
        self._auth_tokens = os.environ.get('DM_API_AUTH_TOKENS')
        os.environ['DM_API_AUTH_TOKENS'] = valid_token

    def do_not_provide_access_token(self):
        self.app.wsgi_app = self.app.wsgi_app.app

    def setup_database(self):
        with self.app.app_context():
            db.create_all()

    def setup_dummy_suppliers(self, n):
        with self.app.app_context():

            for i in range(n):
                db.session.add(
                    Supplier(supplier_id=i, name=u"Supplier {}".format(i))
                )

    def setup_dummy_services_including_unpublished(self, n):
        now = datetime.now()
        with self.app.app_context():
            db.session.add(
                Framework(id=1, expired=False, name="G-Cloud 6")
            )
            self.setup_dummy_suppliers(TEST_SUPPLIERS_COUNT)
            for i in range(n):
                db.session.add(Service(service_id=i,
                                       supplier_id=i % TEST_SUPPLIERS_COUNT,
                                       updated_at=now,
                                       status='published',
                                       created_at=now,
                                       updated_by='tests',
                                       updated_reason='test data',
                                       data={'foo': 'bar'},
                                       framework_id=1))
            # Add extra 'enabled' and 'disabled' services
            db.session.add(Service(service_id=n + 1,
                                   supplier_id=n % TEST_SUPPLIERS_COUNT,
                                   updated_at=now,
                                   status='disabled',
                                   created_at=now,
                                   updated_by='tests',
                                   updated_reason='test data',
                                   data={'foo': 'bar'},
                                   framework_id=1))
            db.session.add(Service(service_id=n + 2,
                                   supplier_id=n % TEST_SUPPLIERS_COUNT,
                                   updated_at=now,
                                   status='enabled',
                                   created_at=now,
                                   updated_by='tests',
                                   updated_reason='test data',
                                   data={'foo': 'bar'},
                                   framework_id=1))
            # Add an extra supplier that will have no services
            db.session.add(
                Supplier(supplier_id=TEST_SUPPLIERS_COUNT, name=u"Supplier {}"
                         .format(TEST_SUPPLIERS_COUNT))
            )

    def teardown(self):
        self.teardown_authorization()
        self.teardown_database()

    def teardown_authorization(self):
        if self._auth_tokens is None:
            del os.environ['DM_API_AUTH_TOKENS']
        else:
            os.environ['DM_API_AUTH_TOKENS'] = self._auth_tokens

    def teardown_database(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def load_example_listing(self, name):
        file_path = os.path.join("example_listings", "{}.json".format(name))
        with open(file_path) as f:
            return json.load(f)

    def first_by_rel(self, rel, links):
        for link in links:
            if link['rel'] == rel:
                return link


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
        assert_in(b'a request that this server could not understand',
                  response.get_data())

    def test_invalid_json_causes_failure(self):
        response = self.client.open(
            self.endpoint,
            method=self.method,
            data='{"not": "valid"}',
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in(b'Invalid JSON', response.get_data())

    def test_invalid_content_type_causes_failure(self):
        response = self.client.open(
            self.endpoint,
            method=self.method,
            data='{"services": {"foo": "bar"}}')

        assert_equal(response.status_code, 400)
        assert_in(b'Unexpected Content-Type', response.get_data())
