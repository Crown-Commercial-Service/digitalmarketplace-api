from flask import json
from nose.tools import assert_equal, assert_in

from app import db
from app.models import Supplier, ContactInformation, AuditEvent
from ..helpers import BaseApplicationTest, JSONUpdateTestMixin


class TestGetSupplier(BaseApplicationTest):
    def setup(self):
        super(TestGetSupplier, self).setup()

        with self.app.app_context():
            payload = self.load_example_listing("Supplier")
            self.supplier = payload
            self.supplier_id = payload['id']

            response = self.client.put(
                '/suppliers/{}'.format(self.supplier_id),
                data=json.dumps({
                    'suppliers': self.supplier
                }),
                content_type='application/json')
            assert_equal(response.status_code, 201)

    def test_get_non_existent_supplier(self):
        response = self.client.get('/suppliers/100')
        assert_equal(404, response.status_code)

    def test_invalid_supplier_id(self):
        response = self.client.get('/suppliers/abc123')
        assert_equal(404, response.status_code)

    def test_get_supplier(self):
        response = self.client.get('/suppliers/{}'.format(self.supplier_id))

        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal(self.supplier_id, data['suppliers']['id'])
        assert_equal(self.supplier['name'], data['suppliers']['name'])

    def test_supplier_clients_exist(self):
        response = self.client.get('/suppliers/{}'.format(self.supplier_id))

        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_in('clients', data['suppliers'].keys())
        assert_equal(3, len(data['suppliers']['clients']))

    def test_supplier_client_key_still_exists_even_without_clients(self):
        # Insert a new supplier with a different id and no clients
        with self.app.app_context():
            new_payload = self.load_example_listing("Supplier")
            new_payload['id'] = 111111
            new_payload['clients'] = []

            response = self.client.put(
                '/suppliers/{}'.format(new_payload['id']),
                data=json.dumps({
                    'suppliers': new_payload
                }),
                content_type='application/json')
            assert_equal(response.status_code, 201)

        response = self.client.get('/suppliers/{}'.format(new_payload['id']))

        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_in('clients', data['suppliers'].keys())
        assert_equal(0, len(data['suppliers']['clients']))


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

    def test_other_prefix_returns_non_alphanumeric_suppliers(self):
        with self.app.app_context():
            db.session.add(
                Supplier(supplier_id=999, name=u"123 Supplier")
            )
            db.session.commit()

            response = self.client.get('/suppliers?prefix=other')

            data = json.loads(response.get_data())
            assert_equal(200, response.status_code)
            assert_equal(1, len(data['suppliers']))
            assert_equal(999, data['suppliers'][0]['id'])
            assert_equal(
                u"123 Supplier",
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

    def test_query_string_prefix_page_out_of_range(self):
        response = self.client.get('/suppliers?prefix=s&page=10')

        assert_equal(response.status_code, 404)

    def test_query_string_prefix_invalid_page_argument(self):
        response = self.client.get('/suppliers?prefix=s&page=a')

        assert_equal(response.status_code, 400)

    def test_below_one_page_number_is_404(self):
        response = self.client.get('/suppliers?page=0')

        assert_equal(response.status_code, 404)


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

    def test_null_clients_list(self):
        with self.app.app_context():
            payload = self.load_example_listing("Supplier")
            del payload['clients']

            response = self.put_import_supplier(payload)
            assert_equal(response.status_code, 201)

            supplier = Supplier.query.filter(
                Supplier.supplier_id == 123456
            ).first()

            assert_equal(supplier.clients, [])

    def test_reinserting_the_same_supplier(self):
        with self.app.app_context():
            payload = self.load_example_listing("Supplier")
            example_listing_contact_information = payload['contactInformation']

            # Exact loop number is arbitrary
            for i in range(3):
                response = self.put_import_supplier(payload)

                assert_equal(response.status_code, 201)

                supplier = Supplier.query.filter(
                    Supplier.supplier_id == 123456
                ).first()
                assert_equal(supplier.name, payload['name'])

                contact_informations = ContactInformation.query.filter(
                    ContactInformation.supplier_id == supplier.supplier_id
                ).all()

                assert_equal(
                    len(example_listing_contact_information),
                    len(contact_informations)
                )

                # Contact Information without a supplier_id should not exist
                contact_informations_no_supplier_id = \
                    ContactInformation.query.filter(
                        ContactInformation.supplier_id == None  # noqa
                    ).all()

                assert_equal(
                    0,
                    len(contact_informations_no_supplier_id)
                )

    def test_cannot_put_to_root_suppliers_url(self):
        payload = self.load_example_listing("Supplier")

        response = self.put_import_supplier(payload, "")
        assert_equal(response.status_code, 405)

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
        for item in ['Invalid JSON must have', 'contactInformation']:
            assert_in(item,
                      json.loads(response.get_data())['error'])

    def test_when_supplier_has_missing_keys(self):
        payload = self.load_example_listing("Supplier")
        payload.pop('id')
        payload.pop('name')

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['Invalid JSON must have', 'id', 'name']:
            assert_in(item,
                      json.loads(response.get_data())['error'])

    def test_when_supplier_contact_information_has_missing_keys(self):
        payload = self.load_example_listing("Supplier")

        payload['contactInformation'][0].pop('email')
        payload['contactInformation'][0].pop('postcode')
        payload['contactInformation'][0].pop('contactName')

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['Invalid JSON must have',
                     'contactName',
                     'email',
                     'postcode']:
            assert_in(item,
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
        for item in ['only-digits-permitted', 'does not match']:
            assert_in(item,
                      json.loads(response.get_data())['error'])

    def test_supplier_esourcing_id_invalid(self):
        payload = self.load_example_listing("Supplier")

        payload.update({'eSourcingId': "only-digits-permitted"})

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['only-digits-permitted', 'does not match']:
            assert_in(item,
                      json.loads(response.get_data())['error'])

    def test_when_supplier_contact_information_email_invalid(self):
        payload = self.load_example_listing("Supplier")

        payload['contactInformation'][0].update({'email': "bad-email-99"})

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['bad-email-99', 'is not a']:
            assert_in(item,
                      json.loads(response.get_data())['error'])


class TestUpdateSupplier(BaseApplicationTest, JSONUpdateTestMixin):
    method = "post"
    endpoint = "/suppliers/123456"

    def setup(self):
        super(TestUpdateSupplier, self).setup()

        with self.app.app_context():
            payload = self.load_example_listing("Supplier")
            self.supplier = payload
            self.supplier_id = payload['id']

            self.client.put('/suppliers/{}'.format(self.supplier_id),
                            data=json.dumps({'suppliers': self.supplier}),
                            content_type='application/json')

    def update_request(self, data):
        return self.client.post(
            self.endpoint,
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_empty_update_supplier(self):
        response = self.update_request({'suppliers': {}})
        assert_equal(response.status_code, 200)

    def test_name_update(self):
        response = self.update_request({'suppliers': {'name': "New Name"}})
        assert_equal(response.status_code, 200)

        with self.app.app_context():
            supplier = Supplier.query.filter(
                Supplier.supplier_id == 123456
            ).first()

            assert_equal(supplier.name, "New Name")

    def test_supplier_update_creates_audit_event(self):
        self.update_request({'suppliers': {'name': "Name"}})

        with self.app.app_context():
            supplier = Supplier.query.filter(
                Supplier.supplier_id == 123456
            ).first()

            audit = AuditEvent.query.filter(
                AuditEvent.object == supplier
            ).first()

            assert_equal(audit.type, "supplier_update")
            assert_equal(audit.data,
                         {"request": {'suppliers': {'name': "Name"}}})

    def test_update_response_matches_payload(self):
        payload = self.load_example_listing("Supplier")
        response = self.update_request({'suppliers': {'name': "New Name"}})
        assert_equal(response.status_code, 200)

        payload.update({'name': 'New Name'})
        supplier = json.loads(response.get_data())['suppliers']

        payload.pop('contactInformation')
        supplier.pop('contactInformation')
        supplier.pop('links')

        assert_equal(supplier, payload)

    def test_update_all_fields(self):
        response = self.update_request({'suppliers': {
            'name': "New Name",
            'description': "New Description",
            'dunsNumber': "010101",
            'eSourcingId': "010101",
            'clients': ["Client1", "Client2"]
        }})

        assert_equal(response.status_code, 200)

        with self.app.app_context():
            supplier = Supplier.query.filter(
                Supplier.supplier_id == 123456
            ).first()

        assert_equal(supplier.name, 'New Name')
        assert_equal(supplier.description, "New Description")
        assert_equal(supplier.duns_number, "010101")
        assert_equal(supplier.esourcing_id, "010101")
        assert_equal(supplier.clients, ["Client1", "Client2"])

    def test_supplier_json_id_does_not_match_oiginal_id(self):
        response = self.update_request({'suppliers': {
            'id': 234567,
            'name': "New Name"
        }})

        assert_equal(response.status_code, 400)

    def test_update_missing_supplier(self):
        response = self.client.post(
            '/suppliers/234567',
            data=json.dumps({'suppliers': {}}),
            content_type='application/json',
        )

        assert_equal(response.status_code, 404)

    def test_links_and_contact_information_are_ignored(self):
        response = self.update_request({'suppliers': {
            'name': "New Name",
            'contactInformation': []
        }, 'links': []})

        with self.app.app_context():
            supplier = Supplier.query.filter(
                Supplier.supplier_id == 123456
            ).first()

        assert_equal(response.status_code, 200)
        assert_equal(len(supplier.contact_information), 2)

    def test_update_with_unexpected_keys(self):
        response = self.update_request({'suppliers': {
            'new_key': "value",
            'name': "New Name"
        }})

        assert_equal(response.status_code, 400)


class TestUpdateContactInformation(BaseApplicationTest):
    def setup(self):
        super(TestUpdateContactInformation, self).setup()

        with self.app.app_context():
            payload = self.load_example_listing("Supplier")
            self.supplier = payload
            self.supplier_id = payload['id']

            response = self.client.put(
                '/suppliers/{}'.format(self.supplier_id),
                data=json.dumps({'suppliers': self.supplier}),
                content_type='application/json')
            supplier = json.loads(response.get_data())['suppliers']
            self.contact_id = supplier['contactInformation'][0]['id']

    def update_request(self, data):
        return self.client.post(
            '/suppliers/123456/contact-information/{}'.format(self.contact_id),
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_empty_update(self):
        response = self.update_request({'contactInformation': {}})
        assert_equal(response.status_code, 200)

    def test_simple_field_update(self):
        response = self.update_request({'contactInformation': {
            'city': "New City"
        }})
        assert_equal(response.status_code, 200)

        with self.app.app_context():
            contact = ContactInformation.query.filter(
                ContactInformation.id == self.contact_id
            ).first()

            assert_equal(contact.city, "New City")

    def test_update_creates_audit_event(self):
        self.update_request({'contactInformation': {
            'city': "New City"
        }})

        with self.app.app_context():
            contact = ContactInformation.query.filter(
                ContactInformation.id == self.contact_id
            ).first()

            audit = AuditEvent.query.filter(
                AuditEvent.object == contact.supplier
            ).first()

            assert_equal(audit.type, "contact_update")
            assert_equal(
                audit.data,
                {"request": {'contactInformation': {'city': "New City"}}}
            )

    def test_update_response_matches_payload(self):
        payload = self.load_example_listing("Supplier")
        response = self.update_request({'contactInformation': {
            'city': "New City"
        }})
        assert_equal(response.status_code, 200)

        payload = payload['contactInformation'][0]
        payload.update({'city': 'New City'})
        payload.pop('links')
        contact = json.loads(response.get_data())['contactInformation']
        contact.pop('id')
        contact.pop('links')

        assert_equal(contact, payload)

    def test_update_all_fields(self):
        response = self.update_request({'contactInformation': {
            "contactName": "New contact",
            "phoneNumber": "New phone",
            "email": "new-value@example.com",
            "website": "example.com",
            "address1": "New address1",
            "address2": "New address2",
            "city": "New city",
            "country": "New country",
            "postcode": "New postcode",
        }})

        assert_equal(response.status_code, 200)

        with self.app.app_context():
            contact = ContactInformation.query.filter(
                ContactInformation.id == self.contact_id
            ).first()

        assert_equal(contact.contact_name, "New contact")
        assert_equal(contact.phone_number, "New phone")
        assert_equal(contact.email, "new-value@example.com")
        assert_equal(contact.website, "example.com")
        assert_equal(contact.address1, "New address1")
        assert_equal(contact.address2, "New address2")
        assert_equal(contact.city, "New city")
        assert_equal(contact.country, "New country")
        assert_equal(contact.postcode, "New postcode")

    def test_supplier_json_id_does_not_match_oiginal_id(self):
        response = self.update_request({'contactInformation': {
            'supplierId': 234567,
            'city': "New City"
        }})

        assert_equal(response.status_code, 400)

    def test_json_id_does_not_match_oiginal_id(self):
        response = self.update_request({'contactInformation': {
            'id': 2,
            'city': "New City"
        }})

        assert_equal(response.status_code, 400)

    def test_update_missing_supplier(self):
        response = self.client.post(
            '/suppliers/234567/contact-information/%s' % self.contact_id,
            data=json.dumps({'contactInformation': {}}),
            content_type='application/json',
        )

        assert_equal(response.status_code, 404)

    def test_update_missing_contact_information(self):
        response = self.client.post(
            '/suppliers/123456/contact-information/100000',
            data=json.dumps({'contactInformation': {}}),
            content_type='application/json',
        )

        assert_equal(response.status_code, 404)

    def test_update_with_unexpected_keys(self):
        response = self.update_request({'contactInformation': {
            'new_key': "value",
            'city': "New City"
        }})

        assert_equal(response.status_code, 400)
