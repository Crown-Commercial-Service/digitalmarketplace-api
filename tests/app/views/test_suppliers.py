from flask import json
from nose.tools import assert_equal, assert_in

from app import db
from app.models import Supplier, ContactInformation
from ..helpers import BaseApplicationTest


class TestGetSupplier(BaseApplicationTest):
    def setup(self):
        super(TestGetSupplier, self).setup()

        with self.app.app_context():
            db.session.add(
                Supplier(
                    supplier_id=585274,
                    name=u"Supplier 585274"
                )
            )
            db.session.add(
                ContactInformation(
                    supplier_id=585274,
                    contact_name=u"Liz",
                    email=u"liz@royal.gov.uk",
                    postcode=u"SW1A 1AA"
                )
            )

    def test_get_non_existent_supplier(self):
        response = self.client.get('/suppliers/100')
        assert_equal(404, response.status_code)

    def test_invalid_supplier_id(self):
        response = self.client.get('/suppliers/abc123')
        assert_equal(404, response.status_code)

    def test_get_supplier(self):
        response = self.client.get('/suppliers/585274')

        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal(585274, data['suppliers']['id'])
        assert_equal(u"Supplier 585274", data['suppliers']['name'])


class TestListSuppliers(BaseApplicationTest):
    def setup(self):
        super(TestListSuppliers, self).setup()

        # Supplier names like u"Supplier {n}"
        self.setup_dummy_suppliers(150)

    def test_query_string_missing(self):
        response = self.client.get('/suppliers')
        assert_equal(200, response.status_code)

    def test_query_string_prefix_empty(self):
        response = self.client.get('/suppliers?prefix=')
        assert_equal(200, response.status_code)

    def test_query_string_prefix_returns_none(self):
        response = self.client.get('/suppliers?prefix=canada')
        assert_equal(404, response.status_code)

    def test_query_string_prefix_sql_injection_wont_work(self):
        response = \
            self.client.get('/suppliers?prefix=;DROP%20TABLE%20suppliers;')
        assert_equal(404, response.status_code)

    def test_query_string_prefix_returns_single(self):
        response = self.client.get('/suppliers?prefix=supplier%20149')

        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal(1, len(data['suppliers']))
        assert_equal(149, data['suppliers'][0]['id'])
        assert_equal(
            u"Supplier 149",
            data['suppliers'][0]['name']
        )

    def test_query_string_prefix_returns_paginated_page_one(self):
        response = self.client.get('/suppliers?prefix=s')
        data = json.loads(response.get_data())

        assert_equal(200, response.status_code)
        assert_equal(100, len(data['suppliers']))
        next_link = self.first_by_rel('next', data['links'])
        assert_in('page=2', next_link['href'])

    def test_query_string_prefix_returns_paginated_page_two(self):
        response = self.client.get('/suppliers?prefix=s&page=2')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['suppliers']), 50)
        prev_link = self.first_by_rel('prev', data['links'])
        assert_in('page=1', prev_link['href'])

    def test_query_string_prefix_page_out_of_range(self):
        response = self.client.get('/suppliers?prefix=s&page=10')

        assert_equal(response.status_code, 404)
        assert_in(b'Page number out of range', response.get_data())

    def test_query_string_prefix_invalid_page_argument(self):
        response = self.client.get('/suppliers?prefix=s&page=a')

        assert_equal(response.status_code, 400)

"""
class TestPutSupplier(BaseApplicationTest, JSONUpdateTestMixin):
    method = "put"
    endpoint = "/suppliers/585274"

    def setup(self):
        super(TestPutSupplier, self).setup()

    def test_add_a_new_supplier(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-Supplier")
            response = self.client.put(
                '/suppliers/585274',
                data=json.dumps(payload),
                content_type='application/json')
            assert_equal(response.status_code, 201)
            supplier = Supplier.query.filter(
                Supplier.supplier_id == 585274
            ).first()
            assert_equal(supplier.name, payload['name'])

    def test_when_supplier_payload_has_invalid_id(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-Supplier")
            payload['id'] = '123abc'
            response = self.client.put(
                '/suppliers/585274',
                data=json.dumps(payload),
                content_type='application/json')
            assert_equal(response.status_code, 400)

    def test_when_supplier_payload_and_route_have_mismatching_ids(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-Supplier")
            payload['id'] = 585275
            response = self.client.put(
                '/suppliers/585274',
                data=json.dumps(payload),
                content_type='application/json')
            assert_equal(response.status_code, 400)
"""
