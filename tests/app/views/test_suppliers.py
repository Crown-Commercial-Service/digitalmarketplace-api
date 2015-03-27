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
        assert_equal(1, data['suppliers']['id'])
        assert_equal(585274, data['suppliers']['supplier_id'])
        assert_equal(u"Supplier 585274", data['suppliers']['name'])
