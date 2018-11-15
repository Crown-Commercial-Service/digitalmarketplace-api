from __future__ import absolute_import

import os
import json
import pytest
import pendulum
import mock
from datetime import timedelta

from nose.tools import assert_equal, assert_in

from app import create_app, db
from app.models import Address, Service, Supplier, Framework, Lot, User, FrameworkLot, \
    Brief, utcnow, Application, PriceSchedule, Product, SupplierFramework

from collections import Mapping, Iterable
from six import string_types
from itertools import tee
from six.moves import zip, zip_longest


TEST_SUPPLIERS_COUNT = 3


COMPLETE_DIGITAL_SPECIALISTS_BRIEF = {
    "essentialRequirements": ["MS Paint", "GIMP"],
    "startDate": "31/12/2016",
    "evaluationType": ["Reference", "Interview"],
    "niceToHaveRequirements": ["LISP"],
    "existingTeam": "Nice people.",
    "specialistWork": "All the things",
    "workingArrangements": "Just get the work done.",
    "organisation": "Org.org",
    "location": "Wales",
    "specialistRole": "developer",
    "title": "I need a Developer",
    "priceWeighting": 85,
    "contractLength": "3 weeks",
    "culturalWeighting": 5,
    "securityClearance": "Developed vetting required.",
    "technicalWeighting": 10,
    "culturalFitCriteria": ["CULTURAL", "FIT"],
    "numberOfSuppliers": 3,
    "summary": "Doing some stuff to help out.",
    "workplaceAddress": "Aviation House",
    "requirementsLength": "2 weeks"
}


INCOMING_APPLICATION_DATA = {
    "representative": "Business Rep",
    "name": "Business Name",
    "abn": "ABN",
    "contact_name": "Rep name",
    "phone": "Rep number",
    "email": "Rep email",
    "summary": "Summary",
    "website": "http://website",
    "linkedin": "",
    "addresses": {
        "0": {
            "address_line": "Add",
            "suburb": "sub",
            "state": "state",
            "postal_code": "2000"
        },
        "1": {
            "address_line": "Add2",
            "suburb": "sub2",
            "state": "state2",
            "postal_code": "3000"
        }
    },
    "case_studies": {
        "c98932c6-b948-08f6-c782-6e3aa83451d4": {
            "approach": "app",
            "client": "client",
            "opportunity": "opp",
            "outcome": [
                "outcome"
            ],
            "project_links": [],
            "roles": "role",
            "service": "Content and publishing",
            "timeframe": "time frame",
            "title": "case study"
        }
    },
    "recruiter_info": {
        "Agile delivery and Governance": {
            "active_candidates": "6",
            "database_size": "5",
            "placed_candidates": "5",
            "margin": "8",
            "markup": "7"
        },
        "Software engineering and Development": {
            "active_candidates": "0",
            "database_size": "9",
            "placed_candidates": "5",
            "margin": "s",
            "markup": "a"
        },
        "Change, Training and Transformation": {
            "active_candidates": "2",
            "database_size": "1",
            "placed_candidates": "5",
            "margin": "4",
            "markup": "3"
        }
    },
    "documents": {
        "financial": {
            "filename": "Marketplace_Frontend_1.png"
        },
        "liability": {
            "expiry": "23131-01-12",
            "filename": "Marketplace_Frontend.png"
        },
        "workers": {
            "expiry": "Invalid Date",
            "filename": "apple-touch-icon_360.png"
        }
    },
    "references": [],
    "services": {
        "Content and publishing": True,
        "User research and design": False
    },
    "steps": {
        "casestudy": "complete",
        "digital": "complete",
        "info": "complete",
        "pricing": "complete",
        "profile": "complete",
        "review": "complete",
        "start": "complete",
        "documents": "complete"
    },
    "products": {
        "0": {
            "name": "product 1",
            "pricing": "http://pricing",
            "summary": "product summary",
            "support": "http://support",
            "website": "http://website"
        },
        "1": {
            "name": "product 2",
            "pricing": "http://pricing2",
            "summary": "product summary2",
            "support": "http://support2",
            "website": "http://website2"
        }
    }
}


def setup_dummy_user(id=123, role='buyer'):
    if User.query.get(id):
        return id
    user = User(
        id=id,
        email_address="test+{}@digital.gov.au".format(id),
        name="my name",
        password="fake password",
        active=True,
        role=role,
        password_changed_at=utcnow()
    )
    db.session.add(user)
    db.session.commit()

    return user.id


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
        self.app.config['SERVER_NAME'] = 'localhost'
        self.client = self.app.test_client()
        self.setup_authorization(self.app)

    def setup_authorization(self, app):
        """Set up bearer token and pass on all requests"""
        valid_token = 'valid-token'
        app.wsgi_app = WSGIApplicationWithEnvironment(
            app.wsgi_app,
            HTTP_AUTHORIZATION='Bearer {}'.format(valid_token))
        self._auth_tokens = app.config['DM_API_AUTH_TOKENS']
        app.config['DM_API_AUTH_TOKENS'] = valid_token

    def do_not_provide_access_token(self):
        self.app.wsgi_app = self.app.wsgi_app.app

    def setup_dummy_user(self, id=123, role='buyer', supplier_code=None):
        with self.app.app_context():
            if User.query.get(id):
                return id
            user = User(
                id=id,
                email_address="test+{}@digital.gov.au".format(id),
                name="my name",
                password="fake password",
                active=True,
                role=role,
                supplier_code=supplier_code,
                password_changed_at=utcnow()
            )
            db.session.add(user)
            db.session.commit()

            return user.id

    def setup_dummy_briefs(self, n, title=None, status='draft', user_id=1, data=None,
                           brief_start=1, lot="digital-specialists", published_at=None):
        user_id = self.setup_dummy_user(id=user_id)

        with self.app.app_context():
            Framework.query.filter(Framework.slug == "digital-outcomes-and-specialists").first()
            lot = Lot.query.filter(Lot.slug == lot).first()
            data = data or COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy()
            data["title"] = title
            for i in range(brief_start, brief_start + n):
                self.setup_dummy_brief(
                    id=i,
                    user_id=user_id,
                    data=data,
                    framework_slug="digital-outcomes-and-specialists",
                    lot_slug=lot.slug,
                    status=status,
                    published_at=published_at,
                )
            db.session.commit()

    def setup_dummy_brief(
        self, id=None, user_id=1, status=None, data=None, published_at=None, withdrawn_at=None,
        framework_slug="digital-outcomes-and-specialists", lot_slug="digital-specialists"
    ):
        if published_at is not None and status is not None:
            raise ValueError("Cannot provide both status and published_at")
        if withdrawn_at is not None and published_at is None:
            raise ValueError("If setting withdrawn_at then published_at must also be set")
        if not published_at:
            if status == 'closed':
                published_at = utcnow() - timedelta(days=1000)
            elif status == 'withdrawn':
                published_at = utcnow() - timedelta(days=1000)
                withdrawn_at = utcnow()
            else:
                published_at = None if status == 'draft' else utcnow()
        framework = Framework.query.filter(Framework.slug == framework_slug).first()
        lot = Lot.query.filter(Lot.slug == lot_slug).first()

        db.session.add(Brief(
            id=id,
            data=data,
            framework=framework,
            lot=lot,
            users=[User.query.get(user_id)],
            published_at=published_at,
            withdrawn_at=withdrawn_at,
        ))

    def setup_dummy_suppliers(self, n):
        with self.app.app_context():
            for i in range(n):
                s = Supplier(
                    code=(i),
                    name=u"Supplier {}".format(i),
                    description="",
                    summary="",
                    addresses=[Address(address_line="{} Dummy Street".format(i),
                                       suburb="Dummy",
                                       state="ZZZ",
                                       postal_code="0000",
                                       country='Australia')],
                    contacts=[],
                    references=[],
                    prices=[],
                )
                db.session.add(s)

            db.session.commit()

    def setup_dummy_suppliers_with_old_and_new_domains(self, n):
        with self.app.app_context():
            framework = Framework.query.filter_by(slug='digital-outcomes-and-specialists').first()
            self.set_framework_status(framework.slug, 'open')

            for i in range(1, n + 1):
                if i == 2:
                    ps = PriceSchedule.from_json({
                        'serviceRole': {
                            'category': 'Technical Architecture, Development, Ethical Hacking and Web Operations',
                            'role': 'Senior Ethical Hacker'},
                        'hourlyRate': 999,
                        'dailyRate': 9999,
                        'gstIncluded': True
                    })
                    prices = [ps]
                else:
                    prices = []

                NON_MATCHING_STRING = 'aaaaaaaaaaaaaaaaa'

                name = "Supplier {}".format(i - 1)
                summary = "suppliers of supplies" if name != 'Supplier 3' else NON_MATCHING_STRING
                name = name if name != 'Supplier 3' else NON_MATCHING_STRING

                t = pendulum.now('UTC')

                s = Supplier(
                    code=i,
                    name=name,
                    abn='1',
                    description="",
                    summary=summary,
                    data={
                        'seller_type': {'sme': True, 'start_up': True}
                    } if i == 2 else {'sme': True, 'start_up': False},
                    addresses=[
                        Address(
                            address_line="{} Dummy Street".format(i),
                            suburb="Dummy",
                            state="ZZZ",
                            postal_code="0000",
                            country='Australia'
                        )
                    ],
                    contacts=[],
                    references=[],
                    prices=prices,
                    last_update_time=t + pendulum.interval(seconds=(i % 3))
                )

                if i == 2:
                    s.add_unassessed_domain('Data science')

                if i == 4:
                    s.add_unassessed_domain('Content and Publishing')

                if i == 3:
                    s.add_unassessed_domain('Content and Publishing')
                    s.add_unassessed_domain('Data science')
                    s.update_domain_assessment_status('Data science', 'assessed')

                p1 = Product(name='zzz {}'.format(i), summary='summary {}'.format(i))
                p2 = Product(name='otherproduct {}'.format(i), summary='othersummary {}'.format(i))

                s.products = [p1, p2]

                sf = SupplierFramework(
                    supplier_code=s.code,
                    framework_id=framework.id,
                    declaration={}
                )

                db.session.add(s)
                db.session.add(sf)

            ds = Supplier(
                name=u"Dummy Supplier",
                abn=Supplier.DUMMY_ABN,
                description="",
                summary="",
                addresses=[Address(address_line="{} Dummy Street".format(i),
                                   suburb="Dummy",
                                   state="ZZZ",
                                   postal_code="0000",
                                   country='Australia')],
                contacts=[],
                references=[],
                prices=prices,
            )

            ds.add_unassessed_domain('Content and Publishing')
            ds.add_unassessed_domain('Data science')
            ds.update_domain_assessment_status('Data science', 'assessed')

            db.session.add(ds)

            sf = SupplierFramework(
                supplier_code=ds.code,
                framework_id=framework.id,
                declaration={}
            )

            db.session.add(sf)
            db.session.commit()

    def setup_additional_dummy_suppliers(self, n, initial):
        with self.app.app_context():
            for i in range(1000, n + 1000):
                db.session.add(
                    Supplier(
                        code=str(i),
                        name=u"{} suppliers Ltd {}".format(initial, i),
                        description="",
                        summary="",
                        addresses=[Address(address_line="{} Additional Street".format(i),
                                           suburb="Additional",
                                           state="ZZZ",
                                           postal_code="0000",
                                           country='Australia')],
                        contacts=[],
                        references=[],
                        prices=[],
                    )
                )
            db.session.commit()

    def setup_dummy_service(self, service_id, supplier_code=1, data=None,
                            status='published', framework_id=1, lot_id=1):
        now = utcnow()
        db.session.add(Service(service_id=service_id,
                               supplier_code=supplier_code,
                               status=status,
                               data=data or {
                                   'serviceName': 'Service {}'.
                                                  format(service_id)
                               },
                               framework_id=framework_id,
                               lot_id=lot_id,
                               created_at=now,
                               updated_at=now))

    def setup_dummy_services(self, n, supplier_code=None, framework_id=1,
                             start_id=0, lot_id=1):
        with self.app.app_context():
            for i in range(start_id, start_id + n):
                self.setup_dummy_service(
                    service_id=str(2000000000 + start_id + i),
                    supplier_code=supplier_code or (i % TEST_SUPPLIERS_COUNT),
                    framework_id=framework_id,
                    lot_id=lot_id
                )

            db.session.commit()

    def setup_dummy_services_including_unpublished(self, n):
        self.setup_dummy_suppliers(TEST_SUPPLIERS_COUNT)
        self.setup_dummy_services(n)
        with self.app.app_context():
            # Add extra 'enabled' and 'disabled' services
            self.setup_dummy_service(
                service_id=str(n + 2000000001),
                supplier_code=n % TEST_SUPPLIERS_COUNT,
                status='disabled')
            self.setup_dummy_service(
                service_id=str(n + 2000000002),
                supplier_code=n % TEST_SUPPLIERS_COUNT,
                status='enabled')
            # Add an extra supplier that will have no services
            db.session.add(
                Supplier(code=TEST_SUPPLIERS_COUNT, name=u"Supplier {}"
                         .format(TEST_SUPPLIERS_COUNT),
                         addresses=[Address(address_line="{} Empty Street".format(TEST_SUPPLIERS_COUNT),
                                            suburb="Empty",
                                            state="ZZZ",
                                            postal_code="0000",
                                            country='Australia')],
                         )
            )
            db.session.commit()

    def teardown(self):
        self.teardown_authorization()
        self.teardown_database()

    def teardown_authorization(self):
        if self._auth_tokens is None:
            del self.app.config['DM_API_AUTH_TOKENS']
        else:
            self.app.config['DM_API_AUTH_TOKENS'] = self._auth_tokens

    def teardown_database(self):
        with self.app.app_context():
            db.session.remove()
            for table in reversed(db.metadata.sorted_tables):
                if table.name not in [
                        "lot",
                        "framework",
                        "framework_lot",
                        "service_category",
                        "service_role",
                        "domain",
                        "agency",
                        "council"]:
                    db.engine.execute(table.delete())
            FrameworkLot.query.filter(FrameworkLot.framework_id >= 100).delete()
            Framework.query.filter(Framework.id >= 100).delete()
            db.session.commit()
            db.get_engine(self.app).dispose()

    def load_example_listing(self, name):
        file_path = os.path.join("example_listings", "{}.json".format(name))
        with open(file_path) as f:
            return json.load(f)

    def string_to_time_to_string(self, value):
        return pendulum.parse(value).to_iso8601_string(extended=True)

    def string_to_time(self, value):
        return pendulum.parse(value)

    def set_framework_status(self, slug, status):
        Framework.query.filter_by(slug=slug).update({'status': status})
        db.session.commit()

    @mock.patch('app.models.get_marketplace_jira')
    def setup_dummy_application(self, mj, data=None):
        if data is None:
            data = self.application_data
        with self.app.app_context():
            application = Application(
                data=data,
            )

            db.session.add(application)
            db.session.flush()

            application.submit_for_approval()
            db.session.commit()

            return application.id

    @property
    def application_data(self):
        return INCOMING_APPLICATION_DATA


class JSONTestMixin(object):
    """
    Tests to verify that endpoints that accept JSON.
    """
    endpoint = None
    method = None
    client = None

    def open(self, **kwargs):
        return self.client.open(
            self.endpoint.format(self=self),
            method=self.method,
            **kwargs
        )

    def test_non_json_causes_failure(self):
        response = self.open(
            data='this is not JSON',
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in(b'Invalid JSON',
                  response.get_data())

    def test_invalid_content_type_causes_failure(self):
        response = self.open(
            data='{"services": {"foo": "bar"}}')

        assert_equal(response.status_code, 400)
        assert_in(b'Unexpected Content-Type', response.get_data())


class JSONUpdateTestMixin(JSONTestMixin):
    @pytest.mark.skipif(True, reason="failing for AU")
    def test_missing_updated_by_should_fail_with_400(self):
        response = self.open(
            data='{}',
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in("'updated_by' is a required property", response.get_data(as_text=True))


def assert_api_compatible(old, new):
    def equality(a, b):
        assert a == b

    for k in old:
        v_old = old[k]
        v_new = new[k]

        if isinstance(v_old, Mapping):
            assert_api_compatible(v_old, v_new)
        elif not isinstance(v_old, string_types) and isinstance(v_old, Iterable):
            for a, b in zip_longest(v_old, v_new):
                assert_api_compatible(a, b)
        else:
            equality(v_old, v_new)


def assert_api_compatible_list(old, new):
    for x0, x1 in zip_longest(old, new):
        assert_api_compatible(x0, x1)


def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def is_sorted(iterable, key=lambda a, b: a <= b):
    return all(key(a, b) for a, b in pairwise(iterable))
