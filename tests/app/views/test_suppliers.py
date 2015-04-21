from flask import json
from nose.tools import assert_equal, assert_in

from app import db
from app.models import Supplier, ContactInformation
from ..helpers import BaseApplicationTest, JSONUpdateTestMixin


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

    def test_supplier_without_contact_information_cannot_be_returned(self):
        with self.app.app_context():
            db.session.delete(
                ContactInformation.query.filter(
                    ContactInformation.supplier_id == 585274
                ).first())

        response = self.client.get('/suppliers/585274')
        assert_equal(404, response.status_code)


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
        assert_equal(404, response.status_code)

    def test_query_string_prefix_returns_single(self):
        response = self.client.get('/suppliers?prefix=supplier%201')

        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal(1, len(data['suppliers']))
        assert_equal(1, data['suppliers'][0]['id'])
        assert_equal(
            u"Supplier 1",
            data['suppliers'][0]['name']
        )

    def test_query_string_prefix_returns_paginated_page_one(self):
        response = self.client.get('/suppliers?prefix=s')
        data = json.loads(response.get_data())

        assert_equal(200, response.status_code)
        assert_equal(5, len(data['suppliers']))
        next_link = self.first_by_rel('next', data['links'])
        assert_in('page=2', next_link['href'])

    def test_query_string_prefix_returns_paginated_page_two(self):
        response = self.client.get('/suppliers?prefix=s&page=2')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['suppliers']), 2)
        prev_link = self.first_by_rel('prev', data['links'])
        assert_in('page=1', prev_link['href'])

    def test_query_string_prefix_page_out_of_range(self):
        response = self.client.get('/suppliers?prefix=s&page=10')

        assert_equal(response.status_code, 404)
        assert_in(b'Page number out of range', response.get_data())

    def test_query_string_prefix_invalid_page_argument(self):
        response = self.client.get('/suppliers?prefix=s&page=a')

        assert_equal(response.status_code, 400)


class TestPutSupplier(BaseApplicationTest, JSONUpdateTestMixin):
    method = "put"
    endpoint = "/suppliers/123456"

    def setup(self):
        super(TestPutSupplier, self).setup()

    def put_import_supplier(self, supplier, route_parameter=None):

        if route_parameter is None:
            route_parameter = '/{}'.format(supplier.get('id', 1))

        return self.client.put(
            '/suppliers' + route_parameter,
            data=json.dumps({
                'suppliers': supplier
            }),
            content_type='application/json')

    def test_add_a_new_supplier(self):
        with self.app.app_context():
            payload = self.load_example_listing("Supplier")
            response = self.put_import_supplier(payload)
            assert_equal(response.status_code, 201)
            supplier = Supplier.query.filter(
                Supplier.supplier_id == 123456
            ).first()
            assert_equal(supplier.name, payload['name'])

    def test_cannot_put_to_root_suppliers_url(self):
        payload = self.load_example_listing("Supplier")

        response = self.put_import_supplier(payload, '')
        assert_equal(response.status_code, 405)
        assert_in('The method is not allowed for the requested URL',
                  response.get_data())

    def test_supplier_json_id_does_not_match_route_id_parameter(self):
        payload = self.load_example_listing("Supplier")

        response = self.put_import_supplier(payload, '/1234567890')
        assert_equal(response.status_code, 400)
        assert_in('id parameter must match id in data',
                  json.loads(response.get_data())['error'])

    def test_when_supplier_has_missing_contact_information(self):
        payload = self.load_example_listing("Supplier")
        payload.pop('contactInformation')

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('Invalid JSON must have '
                  '\'[\'id\', \'name\', \'contactInformation\']\' key(s)',
                  json.loads(response.get_data())['error'])

    def test_when_supplier_has_missing_keys(self):
        payload = self.load_example_listing("Supplier")
        payload.pop('id')
        payload.pop('name')

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('Invalid JSON must have '
                  '\'[\'id\', \'name\', \'contactInformation\']\' key(s)',
                  json.loads(response.get_data())['error'])

    def test_when_supplier_contact_information_has_missing_keys(self):
        payload = self.load_example_listing("Supplier")

        payload['contactInformation'][0].pop('email')
        payload['contactInformation'][0].pop('postcode')
        payload['contactInformation'][0].pop('contactName')

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('Invalid JSON must have '
                  '\'[\'contactName\', \'email\', \'postcode\']\' key(s)',
                  json.loads(response.get_data())['error'])

    def test_when_supplier_has_extra_keys(self):
        payload = self.load_example_listing("Supplier")

        payload.update({'newKey': 1})

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('Additional properties are not allowed',
                  json.loads(response.get_data())['error'])

    def test_when_supplier_contact_information_has_extra_keys(self):
        payload = self.load_example_listing("Supplier")

        payload['contactInformation'][0].update({'newKey': 1})

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('Additional properties are not allowed',
                  json.loads(response.get_data())['error'])

    def test_supplier_duns_number_invalid(self):
        payload = self.load_example_listing("Supplier")

        payload.update({'dunsNumber': "only-digits-permitted"})

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('u\'only-digits-permitted\' does not match u\'^[0-9]+$\'',
                  json.loads(response.get_data())['error'])

    def test_supplier_esourcing_id_invalid(self):
        payload = self.load_example_listing("Supplier")

        payload.update({'eSourcingId': "only-digits-permitted"})

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('u\'only-digits-permitted\' does not match u\'^[0-9]+$\'',
                  json.loads(response.get_data())['error'])

    def test_when_supplier_contact_information_email_invalid(self):
        payload = self.load_example_listing("Supplier")

        payload['contactInformation'][0].update({'email': "bad-email-99"})

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('u\'bad-email-99\' is not a u\'email\'',
                  json.loads(response.get_data())['error'])
