from datetime import datetime
from flask import json
import pytest
from freezegun import freeze_time
from nose.tools import assert_equal, assert_in, assert_is_not_none, assert_true, assert_is

from app import db
from app.models import Address, Supplier, AuditEvent, SupplierFramework, Framework, DraftService, Service
from ..helpers import BaseApplicationTest, JSONTestMixin, JSONUpdateTestMixin
from random import randint


class TestGetSupplier(BaseApplicationTest):
    def setup(self):
        super(TestGetSupplier, self).setup()

        with self.app.app_context():
            payload = self.load_example_listing("Supplier")
            self.supplier = payload
            self.supplier_code = payload['code']

            response = self.client.post(
                '/suppliers'.format(self.supplier_code),
                data=json.dumps({
                    'supplier': self.supplier
                }),
                content_type='application/json')
            assert_equal(response.status_code, 201)

    def test_get_non_existent_supplier(self):
        response = self.client.get('/suppliers/100')
        assert_equal(404, response.status_code)

    def test_invalid_supplier_code(self):
        response = self.client.get('/suppliers/abc123')
        assert_equal(404, response.status_code)

    def test_get_supplier(self):
        response = self.client.get('/suppliers/{}'.format(self.supplier_code))

        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal(self.supplier_code, data['suppliers']['code'])
        assert_equal(self.supplier['name'], data['suppliers']['name'])


class TestListSuppliers(BaseApplicationTest):
    def setup(self):
        super(TestListSuppliers, self).setup()

        # Supplier names like u"Supplier {n}"
        self.setup_dummy_suppliers(7)

    def test_query_string_missing(self):
        response = self.client.get('/suppliers')
        assert_equal(200, response.status_code)

    def test_query_string_prefix_empty(self):
        response = self.client.get('/suppliers?prefix=')
        assert_equal(200, response.status_code)

    def test_query_string_prefix_returns_none(self):
        response = self.client.get('/suppliers?prefix=canada')
        assert_equal(200, response.status_code)
        data = json.loads(response.get_data())
        assert_equal(0, len(data['suppliers']))

    def test_other_prefix_returns_non_alphanumeric_suppliers(self):
        with self.app.app_context():
            db.session.add(
                Supplier(code=999, name=u"999 Supplier",
                         address=Address(address_line="Asdf",
                                         suburb="Asdf",
                                         state="ZZZ",
                                         postal_code="0000",
                                         country='Australia')))
            self.setup_dummy_service(service_id='1230000000', supplier_code=999)
            db.session.commit()

            response = self.client.get('/suppliers?prefix=other')

            data = json.loads(response.get_data())
            assert_equal(200, response.status_code)
            assert_equal(1, len(data['suppliers']))
            assert_equal(999, data['suppliers'][0]['code'])
            assert_equal(
                u"999 Supplier",
                data['suppliers'][0]['name']
            )

    def test_query_string_prefix_returns_paginated_page_one(self):
        response = self.client.get('/suppliers?prefix=s')
        data = json.loads(response.get_data())

        assert_equal(200, response.status_code)
        assert_equal(5, len(data['suppliers']))
        next_link = data['links']['next']
        assert_in('page=2', next_link)

    def test_query_string_prefix_returns_paginated_page_two(self):
        response = self.client.get('/suppliers?prefix=s&page=2')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['suppliers']), 2)
        prev_link = data['links']['prev']
        assert_in('page=1', prev_link)

    def test_query_string_prefix_returns_no_pagination_for_single_page(self):
        self.setup_additional_dummy_suppliers(5, 'T')
        response = self.client.get('/suppliers?prefix=t')
        data = json.loads(response.get_data())

        assert_equal(200, response.status_code)
        assert_equal(5, len(data['suppliers']))
        assert_equal(['self'], list(data['links'].keys()))

    def test_query_string_prefix_page_out_of_range(self):
        response = self.client.get('/suppliers?prefix=s&page=10')

        assert_equal(response.status_code, 404)

    def test_query_string_prefix_invalid_page_argument(self):
        response = self.client.get('/suppliers?prefix=s&page=a')

        assert_equal(response.status_code, 400)

    def test_below_one_page_number_is_404(self):
        response = self.client.get('/suppliers?page=0')

        assert_equal(response.status_code, 404)


class TestUpdateSupplier(BaseApplicationTest, JSONUpdateTestMixin):
    method = "post"
    endpoint = "/suppliers/123456"

    def setup(self):
        super(TestUpdateSupplier, self).setup()

        with self.app.app_context():
            payload = self.load_example_listing("Supplier")
            self.supplier = payload
            self.supplier_code = payload['code']

            self.client.post('/suppliers'.format(self.supplier_code),
                             data=json.dumps({'supplier': self.supplier}),
                             content_type='application/json')

    def update_request(self, data=None, user=None, full_data=None):
        return self.client.post(
            self.endpoint,
            data=json.dumps({
                'supplier': data,
                'updated_by': user or 'supplier@user.dmdev',
            } if full_data is None else full_data),
            content_type='application/json',
        )

    def test_empty_update_supplier(self):
        response = self.update_request({})
        assert_equal(response.status_code, 200)

    def test_name_update(self):
        response = self.update_request({'name': "New Name"})
        assert_equal(response.status_code, 200)

        with self.app.app_context():
            supplier = Supplier.query.filter(
                Supplier.code == 123456
            ).first()

            assert_equal(supplier.name, "New Name")

    def test_supplier_update_creates_audit_event(self):
        self.update_request({'name': "Name"})

        with self.app.app_context():
            supplier = Supplier.query.filter(
                Supplier.code == 123456
            ).first()

            return  # FIXME: auditing not yet implemented in Australian version
            audit = AuditEvent.query.filter(
                AuditEvent.object == supplier
            ).first()

            assert_equal(audit.type, "supplier_update")
            assert_equal(audit.user, "supplier@user.dmdev")
            assert_equal(audit.data, {
                'update': {'name': "Name"},
            })

    def test_update_response_matches_payload(self):
        payload = self.load_example_listing("Supplier")
        response = self.update_request({'name': "New Name"})
        assert_equal(response.status_code, 200)

        payload.update({'name': 'New Name'})
        supplier = json.loads(response.get_data())['suppliers']

        supplier.pop('dataVersion')

        assert (set(supplier.keys()) == set(payload.keys()))
        for key in payload.keys():
            assert supplier[key] == payload[key]

    def test_update_all_fields(self):
        response = self.update_request({
            'name': "New Name",
            'description': "New Description",
        })

        assert_equal(response.status_code, 200)

        with self.app.app_context():
            supplier = Supplier.query.filter(
                Supplier.code == 123456
            ).first()

        assert_equal(supplier.name, 'New Name')
        assert_equal(supplier.description, "New Description")

    def test_update_missing_supplier(self):
        response = self.client.post(
            '/suppliers/234567',
            data=json.dumps({'supplier': {}}),
            content_type='application/json',
        )

        assert_equal(response.status_code, 404)

    def test_update_with_unexpected_keys(self):
        response = self.update_request({
            'new_key': "value",
            'name': "New Name"
        })

        assert_equal(response.status_code, 400)

    def test_update_without_updated_by(self):
        return  # FIXME: updated_by not yet implemented in Australian version
        response = self.update_request(full_data={
            'supplier': {'name': "New Name"},
        })

        assert_equal(response.status_code, 400)


class TestPostSupplier(BaseApplicationTest, JSONTestMixin):
    method = "post"
    endpoint = "/suppliers"

    def setup(self):
        super(TestPostSupplier, self).setup()

    def post_supplier(self, supplier):

        return self.client.post(
            '/suppliers',
            data=json.dumps({
                'supplier': supplier
            }),
            content_type='application/json')

    def test_add_a_new_supplier(self):
        with self.app.app_context():
            payload = self.load_example_listing("new-supplier")
            response = self.post_supplier(payload)
            assert_equal(response.status_code, 201)
            assert_is_not_none(Supplier.query.filter(
                Supplier.name == payload['name']
            ).first())

    def test_when_supplier_has_a_missing_key(self):
        payload = self.load_example_listing("new-supplier")
        payload.pop('name')

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        return  # FIXME: implement useful error message
        for item in ['JSON was not a valid format', '\'name\'', 'is a required property']:
            assert_in(item,
                      json.loads(response.get_data())['error'])

    def test_when_supplier_has_extra_keys(self):
        payload = self.load_example_listing("new-supplier")

        payload.update({'newKey': 1})

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('Additional properties are not allowed',
                  json.loads(response.get_data())['error'])
