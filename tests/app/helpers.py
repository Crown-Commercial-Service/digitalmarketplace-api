from __future__ import absolute_import

import os
import json
from datetime import datetime

from nose.tools import assert_equal, assert_in

from app import create_app, db
from app.models import Service, Supplier, ContactInformation, Framework

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

    config = None

    def setup(self):
        self.app = create_app('test')
        self.client = self.app.test_client()
        self.setup_authorization(self.app)

    def setup_authorization(self, app):
        """Set up bearer token and pass on all requests"""
        valid_token = 'valid-token'
        app.wsgi_app = WSGIApplicationWithEnvironment(
            app.wsgi_app,
            HTTP_AUTHORIZATION='Bearer {}'.format(valid_token))
        self._auth_tokens = os.environ.get('DM_API_AUTH_TOKENS')
        os.environ['DM_API_AUTH_TOKENS'] = valid_token

    def do_not_provide_access_token(self):
        self.app.wsgi_app = self.app.wsgi_app.app

    def setup_dummy_suppliers(self, n):
        with self.app.app_context():
            for i in range(n):
                db.session.add(
                    Supplier(
                        supplier_id=i,
                        name=u"Supplier {}".format(i),
                        description="",
                        clients=[]
                    )
                )
                db.session.add(
                    ContactInformation(
                        supplier_id=i,
                        contact_name=u"Contact for Supplier {}".format(i),
                        email=u"{}@contact.com".format(i),
                        postcode=u"SW1A 1AA"
                    )
                )
            db.session.commit()

    def setup_dummy_framework(self, id=123, name='expired', framework='gcloud',
                              status='expired'):
        db.session.add(Framework(
            id=id,
            name=name,
            framework=framework,
            status=status))

        return id

    def setup_dummy_service(self, service_id, supplier_id=1, data=None,
                            status='published', framework_id=1):
        now = datetime.utcnow()
        db.session.add(Service(service_id=service_id,
                               supplier_id=supplier_id,
                               status=status,
                               data=data or {
                                   'serviceName': 'Service {}'.
                                                  format(service_id)
                               },
                               framework_id=framework_id,
                               created_at=now,
                               updated_at=now))

    def setup_dummy_services_including_unpublished(self, n):
        with self.app.app_context():
            self.setup_dummy_suppliers(TEST_SUPPLIERS_COUNT)
            for i in range(n):
                self.setup_dummy_service(
                    service_id=i,
                    supplier_id=i % TEST_SUPPLIERS_COUNT)
            # Add extra 'enabled' and 'disabled' services
            self.setup_dummy_service(
                service_id=n + 1,
                supplier_id=n % TEST_SUPPLIERS_COUNT,
                status='disabled')
            self.setup_dummy_service(
                service_id=n + 2,
                supplier_id=n % TEST_SUPPLIERS_COUNT,
                status='enabled')
            # Add an extra supplier that will have no services
            db.session.add(
                Supplier(supplier_id=TEST_SUPPLIERS_COUNT, name=u"Supplier {}"
                         .format(TEST_SUPPLIERS_COUNT))
            )
            db.session.add(
                ContactInformation(
                    supplier_id=TEST_SUPPLIERS_COUNT,
                    contact_name=u"Contact for Supplier {}".format(i),
                    email=u"{}@contact.com".format(i),
                    postcode=u"SW1A 1AA"
                )
            )
            db.session.commit()

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
            for table in reversed(db.metadata.sorted_tables):
                if table.name != "frameworks":
                    db.engine.execute(table.delete())
            Framework.query.filter(Framework.id >= 100).delete()
            db.session.commit()
            db.get_engine(self.app).dispose()

    def load_example_listing(self, name):
        file_path = os.path.join("example_listings", "{}.json".format(name))
        with open(file_path) as f:
            return json.load(f)


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
