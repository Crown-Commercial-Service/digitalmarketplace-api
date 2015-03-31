from flask import json
from nose.tools import assert_equal

from app import db
from app.models import Supplier
from ..helpers import BaseApplicationTest


class TestGetSupplier(BaseApplicationTest):
    def setup(self):
        super(TestGetSupplier, self).setup()

        with self.app.app_context():
            db.session.add(
                Supplier(supplier_id=585274, name=u"Supplier 585274")
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


class TestGetSuppliers(BaseApplicationTest):
    def setup(self):
        super(TestGetSuppliers, self).setup()

        with self.app.app_context():
            db.session.add(
                Supplier(supplier_id=585274, name=u"Supplier 585274")
            )
            db.session.add(
                Supplier(supplier_id=123456, name=u"Supplier 123456")
            )
            db.session.add(
                Supplier(
                    supplier_id=3,
                    name=u"Cloudy Clouds Inc Clouded Hosting"
                )
            )

    def test_query_string_missing(self):
        response = self.client.get('/suppliers')
        assert_equal(400, response.status_code)

    def test_query_string_prefix_empty(self):
        response = self.client.get('/suppliers?prefix=')
        assert_equal(400, response.status_code)

    def test_query_string_prefix_returns_none(self):
        response = self.client.get('/suppliers?prefix=canada')
        assert_equal(404, response.status_code)

    def test_query_string_prefix_sql_injection_wont_work(self):
        response = \
            self.client.get('/suppliers?prefix=;DROP%20TABLE%20suppliers;')
        assert_equal(404, response.status_code)

    def test_query_string_prefix_returns_single(self):
        response = self.client.get('/suppliers?prefix=cloud')

        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal(1, len(data['suppliers']))
        assert_equal(3, data['suppliers'][0]['id'])
        assert_equal(
            u"Cloudy Clouds Inc Clouded Hosting",
            data['suppliers'][0]['name']
        )

    def test_query_string_prefix_returns_multiple(self):
        response = self.client.get('/suppliers?prefix=s')

        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal(2, len(data['suppliers']))
        assert_equal(585274, data['suppliers'][0]['id'])
        assert_equal(u"Supplier 123456", data['suppliers'][1]['name'])
