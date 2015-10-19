from __future__ import absolute_import

import os
import json
from datetime import datetime

from nose.tools import assert_equal, assert_in

from app import create_app, db
from app.models import Service, Supplier, ContactInformation, Framework, Lot

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

    def setup_additional_dummy_suppliers(self, n, initial):
        with self.app.app_context():
            for i in range(1000, n+1000):
                db.session.add(
                    Supplier(
                        supplier_id=i,
                        name=u"{} suppliers Ltd {}".format(initial, i),
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

    def setup_dummy_service(self, service_id, supplier_id=1, data=None,
                            status='published', framework_id=1, lot_id=1):
        now = datetime.utcnow()
        db.session.add(Service(service_id=service_id,
                               supplier_id=supplier_id,
                               status=status,
                               data=data or {
                                   'serviceName': 'Service {}'.
                                                  format(service_id)
                               },
                               framework_id=framework_id,
                               lot_id=lot_id,
                               created_at=now,
                               updated_at=now))

    def setup_dummy_services(self, n, supplier_id=None, framework_id=None,
                             start_id=0):
        with self.app.app_context():
            for i in range(start_id, start_id + n):
                self.setup_dummy_service(
                    service_id=str(2000000000 + start_id + i),
                    supplier_id=supplier_id or (i % TEST_SUPPLIERS_COUNT),
                    framework_id=framework_id or 1
                )

            db.session.commit()

    def setup_dummy_services_including_unpublished(self, n):
        self.setup_dummy_suppliers(TEST_SUPPLIERS_COUNT)
        self.setup_dummy_services(n)
        with self.app.app_context():
            # Add extra 'enabled' and 'disabled' services
            self.setup_dummy_service(
                service_id=str(n + 2000000001),
                supplier_id=n % TEST_SUPPLIERS_COUNT,
                status='disabled')
            self.setup_dummy_service(
                service_id=str(n + 2000000002),
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
                    contact_name=u"Contact for Supplier {}".format(
                        TEST_SUPPLIERS_COUNT),
                    email=u"{}@contact.com".format(TEST_SUPPLIERS_COUNT),
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
                if table.name not in ["lots", "frameworks", "framework_lots"]:
                    db.engine.execute(table.delete())
            Framework.query.filter(Framework.id >= 100).delete()
            db.session.commit()
            db.get_engine(self.app).dispose()

    def load_example_listing(self, name):
        file_path = os.path.join("example_listings", "{}.json".format(name))
        with open(file_path) as f:
            return json.load(f)

    def string_to_time_to_string(self, value, from_format, to_format):
        return datetime.strptime(
            value, from_format).strftime(to_format)

    def string_to_time(self, value, from_format):
        return datetime.strptime(
            value, from_format)

    def bootstrap_dos(self):
        old_level = db.session.connection().connection.isolation_level
        db.session.connection().connection.set_isolation_level(0)
        db.session.execute("ALTER TYPE framework_enum ADD VALUE 'dos' AFTER 'gcloud';")
        db.session.execute("ALTER TYPE framework_status_enum ADD VALUE 'coming' BEFORE 'pending';")
        db.session.connection().connection.set_isolation_level(old_level)

        framework = Framework(
            name="Digital Outcomes and Specialists",
            framework='dos', status='open',
            slug='digital-outcomes-and-specialists',
            lots=[
                Lot(name="DOS LOT 1", slug='lot1', one_service_limit=True),
            ]
        )

        db.session.add(framework)
        db.session.commit()


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
        assert_in(b'Invalid JSON',
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
