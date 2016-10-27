from datetime import datetime
from flask import json
import pytest
from freezegun import freeze_time
from nose.tools import assert_equal, assert_in, assert_is_not_none, assert_true, assert_is
from random import randint

from dmapiclient.audit import AuditTypes

from app import db
from app.models import Supplier, ContactInformation, AuditEvent, \
    SupplierFramework, Framework, FrameworkAgreement, DraftService, Service
from ..helpers import BaseApplicationTest, JSONTestMixin, JSONUpdateTestMixin, fixture_params


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
            new_payload['dunsNumber'] = str(randint(111111111, 9999999999))

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

    def test_get_supplier_returns_service_counts(self):
        self.setup_dummy_services(
            5, supplier_id=self.supplier_id, framework_id=1
        )
        self.setup_dummy_services(
            10, start_id=5, supplier_id=self.supplier_id, framework_id=2
        )
        self.setup_dummy_services(
            15, start_id=15, supplier_id=self.supplier_id, framework_id=3
        )

        response = self.client.get('/suppliers/{}'.format(self.supplier_id))

        data = json.loads(response.get_data())
        assert_equal(data['suppliers']['service_counts'], {
            u'G-Cloud 5': 15,
            u'G-Cloud 6': 5
        })


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
                Supplier(supplier_id=999, name=u"999 Supplier")
            )
            self.setup_dummy_service(service_id='1230000000', supplier_id=999)
            db.session.commit()

            response = self.client.get('/suppliers?prefix=other')

            data = json.loads(response.get_data())
            assert_equal(200, response.status_code)
            assert_equal(1, len(data['suppliers']))
            assert_equal(999, data['suppliers'][0]['id'])
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


class TestListSuppliersOnFramework(BaseApplicationTest):

    def setup(self):
        super(TestListSuppliersOnFramework, self).setup()

        with self.app.app_context():
            db.session.add(
                Supplier(supplier_id=1, name=u"Active")
            )
            db.session.add(
                Supplier(supplier_id=2, name=u"Inactive Framework")
            )
            db.session.add(
                Supplier(supplier_id=3, name=u"Unpublished Service")
            )
            self.setup_dummy_service(
                service_id='1000000001', supplier_id=1
            )
            self.setup_dummy_service(
                service_id='1000000004', supplier_id=1, status='enabled'
            )
            self.setup_dummy_service(
                service_id='1000000002', supplier_id=2, framework_id=2
            )
            self.setup_dummy_service(
                service_id='1000000003', supplier_id=3, status='enabled'
            )
            db.session.commit()

    def test_invalid_framework_returns_400(self):
        response = self.client.get('/suppliers?framework=invalid!')
        assert_equal(400, response.status_code)

    def test_should_return_suppliers_on_framework_backwards_compatibility(self):
        # TODO: REMOVE WHEN BUYER APP IS UPDATED
        response = self.client.get('/suppliers?framework=gcloud')
        assert_equal(200, response.status_code)
        data = json.loads(response.get_data())
        assert_equal(1, len(data['suppliers']))
        assert_equal('Active', data['suppliers'][0]['name'])

    def test_should_return_suppliers_on_framework(self):
        response = self.client.get('/suppliers?framework=g-cloud')
        assert_equal(200, response.status_code)
        data = json.loads(response.get_data())
        assert_equal(1, len(data['suppliers']))
        assert_equal('Active', data['suppliers'][0]['name'])

    def test_should_return_no_suppliers_no_framework(self):
        response = self.client.get('/suppliers?framework=bad')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['suppliers']) == 0

    def test_should_return_all_suppliers_if_no_framework(self):
        response = self.client.get('/suppliers')
        assert_equal(200, response.status_code)
        data = json.loads(response.get_data())
        assert_equal(3, len(data['suppliers']))


class TestListSuppliersByDunsNumber(BaseApplicationTest):

    def setup(self):
        super(TestListSuppliersByDunsNumber, self).setup()

        with self.app.app_context():
            db.session.add(
                Supplier(supplier_id=1, name=u"Duns 123", duns_number="123")
            )
            db.session.add(
                Supplier(supplier_id=2, name=u"Duns xyq", duns_number="xyz")
            )
            db.session.commit()

    def test_invalid_duns_number_returns_400(self):
        response = self.client.get('/suppliers?duns_number=invalid!')
        assert_equal(400, response.status_code)

    def test_should_return_suppliers_by_duns_number(self):
        response = self.client.get('/suppliers?duns_number=123')
        assert_equal(200, response.status_code)
        data = json.loads(response.get_data())
        assert_equal(1, len(data['suppliers']))
        assert_equal('Duns 123', data['suppliers'][0]['name'])

    def test_should_return_no_suppliers_if_nonexisting_duns(self):
        response = self.client.get('/suppliers?duns_number=not-existing')
        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal(0, len(data['suppliers']))

    def test_should_return_all_suppliers_if_no_duns_number(self):
        response = self.client.get('/suppliers')
        assert_equal(200, response.status_code)
        data = json.loads(response.get_data())
        assert_equal(2, len(data['suppliers']))


class TestPutSupplier(BaseApplicationTest, JSONTestMixin):
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
        for item in ['Invalid JSON must have', '\'contactInformation\'']:
            assert_in(item,
                      json.loads(response.get_data())['error'])

    def test_when_supplier_has_a_missing_key(self):
        payload = self.load_example_listing("Supplier")
        payload.pop('id')

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['JSON was not a valid format',
                     '\'id\'',
                     'is a required property']:
            assert_in(
                item, json.loads(response.get_data())['error'])

    def test_when_supplier_has_missing_keys(self):
        payload = self.load_example_listing("Supplier")

        # only one key is returned in the error message
        payload.pop('id')
        payload.pop('name')

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['JSON was not a valid format',
                     '\'id\'',
                     'is a required property']:
            assert_in(
                item, json.loads(response.get_data())['error'])

    def test_when_supplier_contact_information_has_a_missing_key(self):
        payload = self.load_example_listing("Supplier")

        payload['contactInformation'][0].pop('email')

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['JSON was not a valid format',
                     '\'email\'',
                     'is a required property']:
            assert_in(
                item, json.loads(response.get_data())['error'])

    def test_when_supplier_contact_information_has_missing_keys(self):
        payload = self.load_example_listing("Supplier")

        # only one key is returned in the error message
        payload['contactInformation'][0].pop('email')
        payload['contactInformation'][0].pop('contactName')

        response = self.put_import_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['JSON was not a valid format',
                     '\'contactName\'',
                     'is a required property']:
            assert_in(
                item, json.loads(response.get_data())['error'])

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

    def update_request(self, data=None, user=None, full_data=None):
        return self.client.post(
            self.endpoint,
            data=json.dumps({
                'suppliers': data,
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
                Supplier.supplier_id == 123456
            ).first()

            assert_equal(supplier.name, "New Name")

    def test_supplier_update_creates_audit_event(self):
        self.update_request({'name': "Name"})

        with self.app.app_context():
            supplier = Supplier.query.filter(
                Supplier.supplier_id == 123456
            ).first()

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

        payload.pop('contactInformation')
        supplier.pop('contactInformation')
        supplier.pop('links')

        assert_equal(supplier, payload)

    def test_update_all_fields(self):
        response = self.update_request({
            'name': "New Name",
            'description': "New Description",
            'companiesHouseNumber': "AA123456",
            'dunsNumber': "010101",
            'eSourcingId': "010101",
            'clients': ["Client1", "Client2"]
        })

        assert_equal(response.status_code, 200)

        with self.app.app_context():
            supplier = Supplier.query.filter(
                Supplier.supplier_id == 123456
            ).first()

        assert_equal(supplier.name, 'New Name')
        assert_equal(supplier.description, "New Description")
        assert_equal(supplier.duns_number, "010101")
        assert_equal(supplier.companies_house_number, "AA123456")
        assert_equal(supplier.esourcing_id, "010101")
        assert_equal(supplier.clients, ["Client1", "Client2"])

    def test_supplier_json_id_does_not_match_original_id(self):
        response = self.update_request({
            'id': 234567,
            'name': "New Name"
        })

        assert_equal(response.status_code, 400)

    def test_update_missing_supplier(self):
        response = self.client.post(
            '/suppliers/234567',
            data=json.dumps({'suppliers': {}}),
            content_type='application/json',
        )

        assert_equal(response.status_code, 404)

    def test_links_and_contact_information_are_ignored(self):
        response = self.update_request(full_data={'suppliers': {
            'name': "New Name",
            'contactInformation': [],
            'links': [],
        }, 'links': [], 'updated_by': 'supplier@user.dmdev'})

        with self.app.app_context():
            supplier = Supplier.query.filter(
                Supplier.supplier_id == 123456
            ).first()

        assert_equal(response.status_code, 200)
        assert_equal(len(supplier.contact_information), 2)

    def test_update_with_unexpected_keys(self):
        response = self.update_request({
            'new_key': "value",
            'name': "New Name"
        })

        assert_equal(response.status_code, 400)

    def test_update_without_updated_by(self):
        response = self.update_request(full_data={
            'suppliers': {'name': "New Name"},
        })

        assert_equal(response.status_code, 400)


class TestUpdateContactInformation(BaseApplicationTest, JSONUpdateTestMixin):
    method = "post"
    endpoint = "/suppliers/123456/contact-information/{self.contact_id}"

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

    def update_request(self, data=None, user=None, full_data=None):
        return self.client.post(
            '/suppliers/123456/contact-information/{}'.format(self.contact_id),
            data=json.dumps({
                'contactInformation': data,
                'updated_by': user or 'supplier@user.dmdev',
            } if full_data is None else full_data),
            content_type='application/json',
        )

    def test_empty_update(self):
        response = self.update_request({})
        assert_equal(response.status_code, 200)

    def test_simple_field_update(self):
        response = self.update_request({
            'city': "New City"
        })
        assert_equal(response.status_code, 200)

        with self.app.app_context():
            contact = ContactInformation.query.filter(
                ContactInformation.id == self.contact_id
            ).first()

            assert_equal(contact.city, "New City")

    def test_update_creates_audit_event(self):
        self.update_request({
            'city': "New City"
        })

        with self.app.app_context():
            contact = ContactInformation.query.filter(
                ContactInformation.id == self.contact_id
            ).first()

            audit = AuditEvent.query.filter(
                AuditEvent.object == contact.supplier
            ).first()

            assert_equal(audit.type, "contact_update")
            assert_equal(audit.user, "supplier@user.dmdev")
            assert_equal(audit.data, {
                'update': {'city': "New City"},
            })

    def test_update_response_matches_payload(self):
        payload = self.load_example_listing("Supplier")
        response = self.update_request({
            'city': "New City"
        })
        assert_equal(response.status_code, 200)

        payload = payload['contactInformation'][0]
        payload.update({'city': 'New City'})
        payload.pop('links')
        contact = json.loads(response.get_data())['contactInformation']
        contact.pop('id')
        contact.pop('links')

        assert_equal(contact, payload)

    def test_update_all_fields(self):
        response = self.update_request({
            "contactName": "New contact",
            "phoneNumber": "New phone",
            "email": "new-value@example.com",
            "website": "example.com",
            "address1": "New address1",
            "address2": "New address2",
            "city": "New city",
            "country": "New country",
            "postcode": "New postcode",
        })

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
        response = self.update_request({
            'supplierId': 234567,
            'city': "New City"
        })

        assert_equal(response.status_code, 400)

    def test_json_id_does_not_match_oiginal_id(self):
        response = self.update_request({
            'id': 2,
            'city': "New City"
        })

        assert_equal(response.status_code, 400)

    def test_update_missing_supplier(self):
        response = self.client.post(
            '/suppliers/234567/contact-information/%s' % self.contact_id,
            data=json.dumps({}),
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
        response = self.update_request({
            'new_key': "value",
            'city': "New City"
        })

        assert_equal(response.status_code, 400)

    def test_update_ignores_links(self):
        response = self.update_request({
            'links': "value",
            'city': "New City"
        })

        assert_equal(response.status_code, 200)

    def test_update_without_updated_by(self):
        response = self.update_request(full_data={
            'contactInformation': {'city': "New City"},
        })

        assert_equal(response.status_code, 400)


class TestSetSupplierDeclarations(BaseApplicationTest, JSONUpdateTestMixin):
    method = 'put'
    endpoint = '/suppliers/0/frameworks/g-cloud-4/declaration'

    def setup(self):
        super(TestSetSupplierDeclarations, self).setup()
        with self.app.app_context():
            framework = Framework(
                slug='test-open',
                name='Test open',
                framework='g-cloud',
                status='open')
            db.session.add(framework)
            db.session.commit()
        self.setup_dummy_suppliers(1)

    def teardown(self):
        super(TestSetSupplierDeclarations, self).teardown()
        with self.app.app_context():
            frameworks = Framework.query.filter(
                Framework.slug.like('test-%')
            ).all()
            for framework in frameworks:
                db.session.delete(framework)
            db.session.commit()

    def test_add_new_declaration(self):
        with self.app.app_context():
            response = self.client.put(
                '/suppliers/0/frameworks/test-open/declaration',
                data=json.dumps({
                    'updated_by': 'testing',
                    'declaration': {
                        'question': 'answer'
                    }
                }),
                content_type='application/json')

            assert_equal(response.status_code, 201)
            answers = SupplierFramework \
                .find_by_supplier_and_framework(0, 'test-open')
            assert_equal(answers.declaration['question'], 'answer')

    def test_add_null_declaration_should_result_in_dict(self):
        with self.app.app_context():
            response = self.client.put(
                '/suppliers/0/frameworks/test-open/declaration',
                data=json.dumps({
                    'updated_by': 'testing',
                    'declaration': None
                }),
                content_type='application/json')

            assert response.status_code == 201
            answers = SupplierFramework \
                .find_by_supplier_and_framework(0, 'test-open')
            assert isinstance(answers.declaration, dict)

    def test_update_existing_declaration(self):
        with self.app.app_context():
            framework_id = Framework.query.filter(
                Framework.slug == 'test-open').first().id
            answers = SupplierFramework(
                supplier_id=0,
                framework_id=framework_id,
                declaration={'question': 'answer'})
            db.session.add(answers)
            db.session.commit()

            response = self.client.put(
                '/suppliers/0/frameworks/test-open/declaration',
                data=json.dumps({
                    'updated_by': 'testing',
                    'declaration': {
                        'question': 'answer2',
                    }
                }),
                content_type='application/json')

            assert_equal(response.status_code, 200)
            supplier_framework = SupplierFramework \
                .find_by_supplier_and_framework(0, 'test-open')
            assert_equal(supplier_framework.declaration['question'], 'answer2')


class TestPostSupplier(BaseApplicationTest, JSONTestMixin):
    method = "post"
    endpoint = "/suppliers"

    def setup(self):
        super(TestPostSupplier, self).setup()

    def post_supplier(self, supplier):

        return self.client.post(
            '/suppliers',
            data=json.dumps({
                'suppliers': supplier
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

    def test_null_clients_list(self):
        with self.app.app_context():
            payload = self.load_example_listing("new-supplier")
            del payload['clients']

            response = self.post_supplier(payload)
            assert_equal(response.status_code, 201)

            supplier = Supplier.query.filter(
                Supplier.name == payload['name']
            ).first()

            assert_equal(supplier.clients, [])

    def test_when_supplier_has_missing_contact_information(self):
        payload = self.load_example_listing("new-supplier")
        payload.pop('contactInformation')

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['Invalid JSON must have', '\'contactInformation\'']:
            assert_in(item,
                      json.loads(response.get_data())['error'])

    def test_when_supplier_has_a_missing_key(self):
        payload = self.load_example_listing("new-supplier")
        payload.pop('name')

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['JSON was not a valid format', '\'name\'', 'is a required property']:
            assert_in(item,
                      json.loads(response.get_data())['error'])

    def test_when_supplier_contact_information_has_a_missing_key(self):
        payload = self.load_example_listing("new-supplier")

        payload['contactInformation'][0].pop('email')

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['JSON was not a valid format', '\'email\'', 'is a required property']:
            assert_in(item,
                      json.loads(response.get_data())['error'])

    def test_when_supplier_has_extra_keys(self):
        payload = self.load_example_listing("new-supplier")

        payload.update({'newKey': 1})

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('Additional properties are not allowed',
                  json.loads(response.get_data())['error'])

    def test_when_supplier_contact_information_has_extra_keys(self):
        payload = self.load_example_listing("new-supplier")

        payload['contactInformation'][0].update({'newKey': 1})

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        assert_in('Additional properties are not allowed',
                  json.loads(response.get_data())['error'])

    def test_supplier_duns_number_invalid(self):
        payload = self.load_example_listing("new-supplier")

        payload.update({'dunsNumber': "only-digits-permitted"})

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['only-digits-permitted', 'does not match']:
            assert_in(item,
                      json.loads(response.get_data())['error'])

    def test_supplier_esourcing_id_invalid(self):
        payload = self.load_example_listing("new-supplier")

        payload.update({'eSourcingId': "only-digits-permitted"})

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['only-digits-permitted', 'does not match']:
            assert_in(item,
                      json.loads(response.get_data())['error'])

    def test_supplier_companies_house_invalid(self):
        payload = self.load_example_listing("new-supplier")

        payload.update({'companiesHouseNumber': "longer-than-allowed"})

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['longer-than-allowed', 'is too long']:
            assert_in(item,
                      json.loads(response.get_data())['error'])

    def test_when_supplier_contact_information_email_invalid(self):
        payload = self.load_example_listing("new-supplier")

        payload['contactInformation'][0].update({'email': "bad-email-99"})

        response = self.post_supplier(payload)
        assert_equal(response.status_code, 400)
        for item in ['bad-email-99', 'is not a']:
            assert_in(item,
                      json.loads(response.get_data())['error'])

    def test_should_not_be_able_to_import_same_duns_number(self):
        payload1 = self.load_example_listing("new-supplier")
        payload2 = self.load_example_listing("new-supplier")

        response = self.post_supplier(payload1)
        assert_equal(response.status_code, 201)
        response = self.post_supplier(payload2)
        assert_equal(response.status_code, 400)
        data = json.loads(response.get_data())
        assert_true('duplicate key value violates unique constraint "ix_suppliers_duns_number"' in data['message'])


class TestGetSupplierFrameworks(BaseApplicationTest):
    def setup(self):
        super(TestGetSupplierFrameworks, self).setup()

        with self.app.app_context():

            db.session.add_all([
                Supplier(supplier_id=1, name=u"Supplier 1"),
                Supplier(supplier_id=2, name=u"Supplier 2"),
                Supplier(supplier_id=3, name=u"Supplier 2"),
                SupplierFramework(
                    supplier_id=1,
                    framework_id=1,
                    declaration={},
                    on_framework=False
                ),
                SupplierFramework(
                    supplier_id=2,
                    framework_id=1,
                    declaration={},
                    on_framework=False
                ),
                DraftService(
                    framework_id=1,
                    lot_id=1,
                    service_id="0987654321",
                    supplier_id=1,
                    data={},
                    status='not-submitted'
                ),
                DraftService(
                    framework_id=1,
                    lot_id=2,
                    service_id="1234567890",
                    supplier_id=1,
                    data={},
                    status='submitted'
                ),
                Service(
                    framework_id=1,
                    lot_id=2,
                    service_id="1234567890",
                    supplier_id=2,
                    data={},
                    status='published'
                )
            ])
            db.session.commit()

    def test_supplier_with_drafts(self):
        response = self.client.get('/suppliers/1/frameworks')
        data = json.loads(response.get_data())
        assert_equal(response.status_code, 200)
        assert_equal(
            data,
            {
                'frameworkInterest': [
                    {
                        'agreementReturned': False,
                        'agreementReturnedAt': None,
                        'onFramework': False,
                        'declaration': {},
                        'frameworkSlug': 'g-cloud-6',
                        'supplierId': 1,
                        'drafts_count': 1,
                        'complete_drafts_count': 1,
                        'services_count': 0,
                        'supplierName': 'Supplier 1',
                        'agreementDetails': None,
                        'agreementPath': None,
                        'countersigned': False,
                        'countersignedAt': None,
                        'countersignedDetails': None,
                        'countersignedPath': None,
                        'agreementStatus': None,
                        'agreementId': None,
                        'agreedVariations': {},
                    }
                ]
            }
        )

    def test_supplier_with_service(self):
        response = self.client.get('/suppliers/2/frameworks')
        data = json.loads(response.get_data())
        assert_equal(response.status_code, 200)
        assert_equal(
            data,
            {
                'frameworkInterest': [
                    {
                        'agreementReturned': False,
                        'agreementReturnedAt': None,
                        'onFramework': False,
                        'declaration': {},
                        'frameworkSlug': 'g-cloud-6',
                        'supplierId': 2,
                        'drafts_count': 0,
                        'complete_drafts_count': 0,
                        'services_count': 1,
                        'supplierName': 'Supplier 2',
                        'agreementDetails': None,
                        'agreementPath': None,
                        'countersigned': False,
                        'countersignedAt': None,
                        'countersignedDetails': None,
                        'countersignedPath': None,
                        'agreementStatus': None,
                        'agreementId': None,
                        'agreedVariations': {},
                    }
                ]
            }
        )

    def test_supplier_with_no_drafts_or_services(self):
        response = self.client.get('/suppliers/3/frameworks')
        data = json.loads(response.get_data())
        assert_equal(response.status_code, 200)
        assert_equal(
            data,
            {
                'frameworkInterest': []
            }
        )

    def test_supplier_that_doesnt_exist(self):
        response = self.client.get('/suppliers/4/frameworks')
        data = json.loads(response.get_data())
        assert_equal(response.status_code, 404)


class TestRegisterFrameworkInterest(BaseApplicationTest, JSONUpdateTestMixin):
    method = "put"
    endpoint = "/suppliers/1/frameworks/digital-outcomes-and-specialists"

    def setup(self):
        super(TestRegisterFrameworkInterest, self).setup()

        with self.app.app_context():
            self.set_framework_status('digital-outcomes-and-specialists', 'open')

            db.session.add(
                Supplier(supplier_id=1, name=u"Supplier 1")
            )
            db.session.add(
                ContactInformation(
                    supplier_id=1,
                    contact_name=u"Liz",
                    email=u"liz@royal.gov.uk",
                    postcode=u"SW1A 1AA"
                )
            )
            db.session.commit()

    def register_interest(self, supplier_id, framework_slug, user='interested@example.com'):
        return self.client.put(
            '/suppliers/{}/frameworks/{}'.format(supplier_id, framework_slug),
            data=json.dumps({'updated_by': user}),
            content_type='application/json')

    def test_can_register_interest_in_open_framework(self):
        with self.app.app_context():
            response = self.register_interest(1, 'digital-outcomes-and-specialists')

            assert_equal(response.status_code, 201)
            data = json.loads(response.get_data())
            assert_equal(data['frameworkInterest']['supplierId'], 1)
            assert_equal(data['frameworkInterest']['frameworkSlug'], 'digital-outcomes-and-specialists')
            assert isinstance(data['frameworkInterest']['declaration'], dict)

    def test_can_not_register_interest_in_not_open_framework_(self):
        with self.app.app_context():
            response = self.register_interest(1, 'g-cloud-5')

            assert_equal(response.status_code, 400)
            data = json.loads(response.get_data())
            assert_equal(data['error'], "'g-cloud-5' framework is not open")

    def test_can_not_register_interest_more_than_once_in_open_framework(self):
        with self.app.app_context():
            response1 = self.register_interest(1, 'digital-outcomes-and-specialists')
            assert_equal(response1.status_code, 201)
            data = json.loads(response1.get_data())
            assert_equal(data['frameworkInterest']['supplierId'], 1)
            assert_equal(data['frameworkInterest']['frameworkSlug'], 'digital-outcomes-and-specialists')

            response2 = self.register_interest(1, 'digital-outcomes-and-specialists', user='another@example.com')
            assert_equal(response2.status_code, 200)
            data = json.loads(response2.get_data())
            assert_equal(data['frameworkInterest']['supplierId'], 1)
            assert_equal(data['frameworkInterest']['frameworkSlug'], 'digital-outcomes-and-specialists')

    def test_can_not_send_payload_to_register_interest_endpoint(self):
        with self.app.app_context():
            response = self.client.put(
                '/suppliers/1/frameworks/digital-outcomes-and-specialists',
                data=json.dumps(
                    {
                        'updated_by': 'interested@example.com',
                        'update': {'agreementReturned': True}
                    }),
                content_type='application/json')

            assert_equal(response.status_code, 400)
            data = json.loads(response.get_data())
            assert_equal(data['error'], 'This PUT endpoint does not take a payload.')

    def test_register_interest_creates_audit_event(self):
        self.register_interest(1, 'digital-outcomes-and-specialists')

        with self.app.app_context():
            supplier = Supplier.query.filter(
                Supplier.supplier_id == 1
            ).first()

            audit = AuditEvent.query.filter(
                AuditEvent.object == supplier
            ).first()

            assert_equal(audit.type, "register_framework_interest")
            assert_equal(audit.user, "interested@example.com")
            assert_equal(audit.data['supplierId'], 1)
            assert_equal(audit.data['frameworkSlug'], 'digital-outcomes-and-specialists')

    def test_can_get_registered_frameworks_for_a_supplier(self):
        with self.app.app_context():
            response1 = self.client.get("/suppliers/1/frameworks/interest")
            assert_equal(response1.status_code, 200)
            data = json.loads(response1.get_data())
            assert_equal(data['frameworks'], [])

            self.register_interest(1, 'digital-outcomes-and-specialists')

            response2 = self.client.get("/suppliers/1/frameworks/interest")
            assert_equal(response2.status_code, 200)
            data = json.loads(response2.get_data())
            assert_equal(data['frameworks'], ['digital-outcomes-and-specialists'])


@fixture_params('supplier_framework', {
    'on_framework': True,
    'declaration': {'an_answer': 'Yes it is'},
})
class TestSupplierFrameworkResponse(BaseApplicationTest):
    def test_get_supplier_framework_info_when_no_framework_agreement(self, supplier_framework):
        # Get SupplierFramework record
        response = self.client.get(
            '/suppliers/{}/frameworks/{}'.format(supplier_framework['supplierId'], supplier_framework['frameworkSlug']))

        data = json.loads(response.get_data())
        assert response.status_code, 200
        assert data['frameworkInterest']['supplierId'] == supplier_framework['supplierId']
        assert data['frameworkInterest']['frameworkSlug'] == supplier_framework['frameworkSlug']
        assert data['frameworkInterest']['declaration'] == {'an_answer': 'Yes it is'}
        assert data['frameworkInterest']['onFramework'] is True
        assert data['frameworkInterest']['agreementReturned'] is False
        assert data['frameworkInterest']['agreementReturnedAt'] is None
        assert data['frameworkInterest']['countersigned'] is False
        assert data['frameworkInterest']['countersignedAt'] is None
        assert data['frameworkInterest']['agreementDetails'] is None
        assert data['frameworkInterest']['agreementStatus'] is None

    def test_get_supplier_framework_does_not_return_draft_framework_agreement(self, supplier_framework):
        with self.app.app_context():
            supplier_framework_object = SupplierFramework.find_by_supplier_and_framework(
                supplier_framework['supplierId'], supplier_framework['frameworkSlug']
            )

            framework_agreement = FrameworkAgreement(
                supplier_framework=supplier_framework_object,
                signed_agreement_details={
                    u'signerName': u'thing 2',
                    u'signerRole': u'thing 2',
                    u'uploaderUserId': 30
                },
            )
            db.session.add(framework_agreement)
            db.session.commit()

            # Get back the SupplierFramework record
            response = self.client.get(
                '/suppliers/{}/frameworks/{}'.format(
                    supplier_framework['supplierId'], supplier_framework['frameworkSlug']
                )
            )

            data = json.loads(response.get_data())
            assert response.status_code, 200
            assert 'frameworkInterest' in data
            assert data['frameworkInterest'] == {
                'supplierId': supplier_framework['supplierId'],
                'supplierName': 'Supplier name',
                'frameworkSlug': supplier_framework['frameworkSlug'],
                'declaration': {'an_answer': 'Yes it is'},
                'onFramework': True,
                'agreementId': None,
                'agreementReturned': False,
                'agreementReturnedAt': None,
                'agreementDetails': None,
                'agreementPath': None,
                'countersigned': False,
                'countersignedAt': None,
                'countersignedDetails': None,
                'countersignedPath': None,
                'agreementStatus': None,
                'agreedVariations': {}
            }

    def test_get_supplier_framework_returns_signed_framework_agreement(self, supplier_framework):
        with self.app.app_context():
            supplier_framework_object = SupplierFramework.find_by_supplier_and_framework(
                supplier_framework['supplierId'], supplier_framework['frameworkSlug']
            )

            framework_agreement = FrameworkAgreement(
                supplier_framework=supplier_framework_object,
                signed_agreement_details={
                    u'signerName': u'thing 2',
                    u'signerRole': u'thing 2',
                    u'uploaderUserId': 30
                },
                signed_agreement_path='/agreement.pdf',
                signed_agreement_returned_at=datetime(2017, 1, 1, 1, 1, 1),
            )
            db.session.add(framework_agreement)
            db.session.commit()

            # Get back the SupplierFramework record
            response = self.client.get(
                '/suppliers/{}/frameworks/{}'.format(
                    supplier_framework['supplierId'], supplier_framework['frameworkSlug']
                )
            )

            data = json.loads(response.get_data())
            assert response.status_code, 200
            assert 'frameworkInterest' in data, data
            assert data['frameworkInterest'] == {
                'supplierId': supplier_framework['supplierId'],
                'supplierName': 'Supplier name',
                'frameworkSlug': supplier_framework['frameworkSlug'],
                'declaration': {'an_answer': 'Yes it is'},
                'onFramework': True,
                'agreementId': framework_agreement.id,
                'agreementReturned': True,
                'agreementReturnedAt': '2017-01-01T01:01:01.000000Z',
                'agreementPath': '/agreement.pdf',
                'countersigned': False,
                'countersignedAt': None,
                'countersignedDetails': None,
                'countersignedPath': None,
                'agreementDetails': {
                    'signerName': 'thing 2',
                    'signerRole': 'thing 2',
                    'uploaderUserId': 30
                },
                'agreementStatus': 'signed',
                'agreedVariations': {}
            }

    def test_get_supplier_framework_returns_countersigned_framework_agreement(self, supplier_framework, supplier):
        with self.app.app_context():
            supplier_framework_object = SupplierFramework.find_by_supplier_and_framework(
                supplier_framework['supplierId'], supplier_framework['frameworkSlug']
            )

            framework_agreement = FrameworkAgreement(
                supplier_framework=supplier_framework_object,
                signed_agreement_details={
                    u'signerName': u'thing 2',
                    u'signerRole': u'thing 2',
                    u'uploaderUserId': 30
                },
                signed_agreement_path='/agreement.pdf',
                signed_agreement_returned_at=datetime(2017, 1, 1, 1, 1, 1),
                countersigned_agreement_details={
                    'some': 'data'
                },
                countersigned_agreement_returned_at=datetime(2017, 2, 1, 1, 1, 1),
                countersigned_agreement_path='path'
            )
            db.session.add(framework_agreement)
            db.session.commit()

            # Get back the SupplierFramework record
            response = self.client.get(
                '/suppliers/{}/frameworks/{}'.format(
                    supplier_framework['supplierId'], supplier_framework['frameworkSlug']
                )
            )

            data = json.loads(response.get_data())
            assert response.status_code, 200
            assert 'frameworkInterest' in data
            assert data['frameworkInterest'] == {
                'supplierId': supplier_framework['supplierId'],
                'supplierName': 'Supplier name',
                'frameworkSlug': supplier_framework['frameworkSlug'],
                'declaration': {'an_answer': 'Yes it is'},
                'onFramework': True,
                'agreementId': framework_agreement.id,
                'agreementReturned': True,
                'agreementReturnedAt': '2017-01-01T01:01:01.000000Z',
                'agreementDetails': {
                    'signerName': 'thing 2',
                    'signerRole': 'thing 2',
                    'uploaderUserId': 30
                },
                'agreementPath': '/agreement.pdf',
                'countersigned': True,
                'countersignedAt': '2017-02-01T01:01:01.000000Z',
                'countersignedDetails': {'some': 'data'},
                'countersignedPath': 'path',
                'agreementStatus': 'countersigned',
                'agreedVariations': {}
            }

    def test_get_supplier_framework_info_with_non_existent_framework(self, supplier_framework):
        response = self.client.get(
            '/suppliers/{}/frameworks/{}'.format(supplier_framework['supplierId'], 'g-cloud-5'))

        assert response.status_code == 404

    def test_get_supplier_framework_info_with_non_existent_supplier(self, supplier_framework):
        response = self.client.get(
            '/suppliers/{}/frameworks/{}'.format(0, supplier_framework['frameworkSlug']))

        assert response.status_code == 404


class TestSupplierFrameworkUpdates(BaseApplicationTest):
    def supplier_framework_interest(self, supplier_framework, update):
        url = '/suppliers/{}/frameworks/{}'.format(
            supplier_framework['supplierId'], supplier_framework['frameworkSlug'])

        # Update the SupplierFramework record
        return self.client.post(
            url,
            data=json.dumps(
                {
                    'updated_by': 'interested@example.com',
                    'frameworkInterest': update
                }),
            content_type='application/json')

    def test_adding_supplier_has_passed(self, supplier_framework):
        response = self.supplier_framework_interest(
            supplier_framework,
            update={'onFramework': True}
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['supplierId'] == supplier_framework['supplierId']
        assert data['frameworkInterest']['frameworkSlug'] == supplier_framework['frameworkSlug']
        assert data['frameworkInterest']['onFramework'] is True

    def test_adding_supplier_has_not_passed(self, supplier_framework):
        response = self.supplier_framework_interest(
            supplier_framework,
            update={'onFramework': False}
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['supplierId'] == supplier_framework['supplierId']
        assert data['frameworkInterest']['frameworkSlug'] == supplier_framework['frameworkSlug']
        assert data['frameworkInterest']['onFramework'] is False

    def test_changing_on_framework_from_failed_to_passed(self, supplier_framework):
        response = self.supplier_framework_interest(
            supplier_framework,
            update={'onFramework': False}
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['onFramework'] is False
        assert data['frameworkInterest']['agreementReturned'] is False

        response2 = self.supplier_framework_interest(
            supplier_framework,
            update={'onFramework': True}
        )
        assert response2.status_code, 200
        data = json.loads(response2.get_data())
        assert data['frameworkInterest']['onFramework'] is True
        assert data['frameworkInterest']['agreementReturned'] is False

    def test_changing_on_framework_from_passed_to_failed(self, supplier_framework):
        response = self.supplier_framework_interest(
            supplier_framework,
            update={'onFramework': True}
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['onFramework'] is True
        assert data['frameworkInterest']['agreementReturned'] is False

        response2 = self.supplier_framework_interest(
            supplier_framework,
            update={'onFramework': False}
        )
        assert response2.status_code == 200
        data = json.loads(response2.get_data())
        assert data['frameworkInterest']['onFramework'] is False
        assert data['frameworkInterest']['agreementReturned'] is False

    def test_changing_on_framework_to_passed_creates_audit_event(self, supplier_framework):
        self.supplier_framework_interest(
            supplier_framework,
            update={'onFramework': True}
        )
        with self.app.app_context():
            supplier = Supplier.query.filter(
                Supplier.supplier_id == supplier_framework['supplierId']
            ).first()
            audit = AuditEvent.query.filter(
                AuditEvent.object == supplier,
                AuditEvent.type == "supplier_update"
            ).first()
            assert audit.type == "supplier_update"
            assert audit.user == "interested@example.com"
            assert audit.data['supplierId'] == supplier_framework['supplierId']
            assert audit.data['frameworkSlug'] == supplier_framework['frameworkSlug']
            assert audit.data['update']['onFramework'] is True

    def test_can_only_update_on_framework_with_this_route(self, supplier_framework):
        response = self.supplier_framework_interest(
            supplier_framework,
            update={'onFramework': True, 'agreementReturned': True}
        )
        assert response.status_code == 400
        error_message = json.loads(response.get_data(as_text=True))['error']
        assert error_message == "Invalid JSON must only have ['onFramework'] keys"


class TestSupplierFrameworkVariation(BaseApplicationTest):
    def setup(self):
        super(TestSupplierFrameworkVariation, self).setup()
        self.setup_dummy_suppliers(1)
        self.setup_dummy_user(1, role='supplier')
        self.supplier_id = 0

    def test_agree_variation_fails_with_no_supplier_framework(self, live_g8_framework_2_variations):
        response = self.client.put("/suppliers/0/frameworks/g-cloud-8/variation/banana", data=json.dumps({
            "updated_by": "test123",
            "agreedVariations": {
                "agreedUserId": 1,
            },
        }), content_type="application/json")

        assert response.status_code == 404

        response2 = self.client.get("/suppliers/1/frameworks/g-cloud-8")
        assert response2.status_code == 404

    def test_agree_variation_fails_with_supplier_not_on_framework(
            self,
            live_g8_framework_2_variations_suppliers_not_on_framework,
            ):
        response = self.client.put("/suppliers/1/frameworks/g-cloud-8/variation/banana", data=json.dumps({
            "updated_by": "test123",
            "agreedVariations": {
                "agreedUserId": 1,
            },
        }), content_type="application/json")

        assert response.status_code == 404

        response2 = self.client.get("/suppliers/1/frameworks/g-cloud-8")
        assert response2.status_code == 200
        assert not json.loads(response2.get_data())["frameworkInterest"]["agreedVariations"]

    def test_agree_variation_fails_with_invalid_variation(
            self,
            live_g8_framework_2_variations_suppliers_on_framework,
            ):
        response = self.client.put("/suppliers/1/frameworks/g-cloud-8/variation/mango", data=json.dumps({
            "updated_by": "test123",
            "agreedVariations": {
                "agreedUserId": 1,
            },
        }), content_type="application/json")

        assert response.status_code == 404

        response2 = self.client.get("/suppliers/1/frameworks/g-cloud-8")
        assert response2.status_code == 200
        assert not json.loads(response2.get_data())["frameworkInterest"]["agreedVariations"]

    def test_agree_variation_fails_with_no_framework_variations(
            self,
            live_g8_framework_suppliers_on_framework,
            ):
        response = self.client.put("/suppliers/1/frameworks/g-cloud-8/variation/banana", data=json.dumps({
            "updated_by": "test123",
            "agreedVariations": {
                "agreedUserId": 1,
            },
        }), content_type="application/json")

        assert response.status_code == 404

        response2 = self.client.get("/suppliers/1/frameworks/g-cloud-8")
        assert response2.status_code == 200
        assert not json.loads(response2.get_data())["frameworkInterest"]["agreedVariations"]

    def test_agree_variation_fails_with_unrelated_user_id(
            self,
            live_g8_framework_2_variations_suppliers_on_framework_with_alt,
            ):
        response = self.client.put("/suppliers/1/frameworks/g-cloud-8/variation/banana", data=json.dumps({
            "updated_by": "test123",
            "agreedVariations": {
                # the "alt", unrelated, user
                "agreedUserId": 2,
            },
        }), content_type="application/json")

        assert response.status_code == 403

        response2 = self.client.get("/suppliers/1/frameworks/g-cloud-8")
        assert response2.status_code == 200
        assert not json.loads(response2.get_data())["frameworkInterest"]["agreedVariations"]

        # let's also check it hasn't gone & done something crazy like flipped the "alt" user/supplier's agreement flag
        response3 = self.client.get("/suppliers/2/frameworks/g-cloud-8")
        assert response3.status_code == 200
        assert not json.loads(response3.get_data())["frameworkInterest"]["agreedVariations"]

    def test_agree_variation_fails_with_invalid_user_id(
            self,
            live_g8_framework_2_variations_suppliers_on_framework,
            ):
        response = self.client.put("/suppliers/1/frameworks/g-cloud-8/variation/banana", data=json.dumps({
            "updated_by": "test123",
            "agreedVariations": {
                "agreedUserId": 314159,
            },
        }), content_type="application/json")

        assert response.status_code == 400

        response2 = self.client.get("/suppliers/1/frameworks/g-cloud-8")
        assert response2.status_code == 200
        assert not json.loads(response2.get_data())["frameworkInterest"]["agreedVariations"]

    def test_agree_variation_succeeds(
            self,
            app,
            live_g8_framework_2_variations_suppliers_on_framework_with_alt,
            ):
        with freeze_time('2016-06-06'):
            response = self.client.put("/suppliers/1/frameworks/g-cloud-8/variation/banana", data=json.dumps({
                "updated_by": "test123",
                "agreedVariations": {
                    "agreedUserId": 1,
                },
            }), content_type="application/json")

        expected_variation = {
            "agreedUserId": 1,
            "agreedUserEmail": "test+1@digital.gov.uk",
            "agreedUserName": "my name",
            "agreedAt": "2016-06-06T00:00:00.000000Z",
        }

        assert response.status_code == 200
        response_json = json.loads(response.get_data())
        assert response_json["agreedVariations"] == expected_variation

        response2 = self.client.get("/suppliers/1/frameworks/g-cloud-8")
        assert response2.status_code == 200
        assert json.loads(response2.get_data())["frameworkInterest"]["agreedVariations"] == {
            "banana": expected_variation,
        }

        with app.app_context():
            audit_events = AuditEvent.query.filter(
                AuditEvent.type == "agree_framework_variation"
            ).order_by(AuditEvent.created_at, AuditEvent.id).all()

            assert len(audit_events) == 1

            assert audit_events[0].user == "test123"
            assert audit_events[0].data["supplierId"] == 1
            assert audit_events[0].data["frameworkSlug"] == "g-cloud-8"
            assert audit_events[0].data["variationSlug"] == "banana"
            assert audit_events[0].data["update"] == {
                "agreedUserId": 1,
            }

    def test_agree_variation_various(
            self,
            app,
            live_g8_framework_2_variations_suppliers_on_framework_with_alt,
            ):
        # this test tests quite a few things in one. in an ideal world all these things would be tested separately,
        # but some of these features require me to build up a bit of prior state for them to come in to play and my
        # reasoning is that i may as well be testing those bits i'm using to set things up as i set them up. this way
        # gives me the most bang for the buck.

        with freeze_time('2016-06-06'):
            response = self.client.put("/suppliers/2/frameworks/g-cloud-8/variation/toblerone", data=json.dumps({
                "updated_by": "test123",
                "agreedVariations": {
                    "agreedUserId": 2,
                },
            }), content_type="application/json")

        expected_variation_toblerone = {
            "agreedUserId": 2,
            "agreedUserEmail": "test+2@digital.gov.uk",
            "agreedUserName": "my name",
            "agreedAt": "2016-06-06T00:00:00.000000Z",
        }

        assert response.status_code == 200
        response_json = json.loads(response.get_data())
        assert response_json["agreedVariations"] == expected_variation_toblerone

        response2 = self.client.get("/suppliers/2/frameworks/g-cloud-8")
        assert response2.status_code == 200
        assert json.loads(response2.get_data())["frameworkInterest"]["agreedVariations"] == {
            "toblerone": expected_variation_toblerone,
        }

        # check we've left the other supplier alone
        response3 = self.client.get("/suppliers/1/frameworks/g-cloud-8")
        assert response3.status_code == 200
        assert not json.loads(response3.get_data())["frameworkInterest"]["agreedVariations"]

        with freeze_time("2016-07-07"):
            response4 = self.client.put("/suppliers/2/frameworks/g-cloud-8/variation/banana", data=json.dumps({
                "updated_by": "test123",
                "agreedVariations": {
                    "agreedUserId": 2,
                },
            }), content_type="application/json")

        expected_variation_banana = {
            "agreedUserId": 2,
            "agreedUserEmail": "test+2@digital.gov.uk",
            "agreedUserName": "my name",
            "agreedAt": "2016-07-07T00:00:00.000000Z",
        }

        assert response4.status_code == 200
        response4_json = json.loads(response4.get_data())
        assert response4_json["agreedVariations"] == expected_variation_banana

        response5 = self.client.get("/suppliers/2/frameworks/g-cloud-8")
        assert response5.status_code == 200
        assert json.loads(response5.get_data())["frameworkInterest"]["agreedVariations"] == {
            "banana": expected_variation_banana,
            "toblerone": expected_variation_toblerone,
        }

        # check we can't agree a second time
        response6 = self.client.put("/suppliers/2/frameworks/g-cloud-8/variation/toblerone", data=json.dumps({
            "updated_by": "test123",
            "agreedVariations": {
                "agreedUserId": 2,
            },
        }), content_type="application/json")
        assert response6.status_code == 400

        # check that really didn't alter anything
        response7 = self.client.get("/suppliers/2/frameworks/g-cloud-8")
        assert response7.status_code == 200
        assert json.loads(response7.get_data())["frameworkInterest"]["agreedVariations"] == {
            "banana": expected_variation_banana,
            "toblerone": expected_variation_toblerone,
        }

        with app.app_context():
            audit_events = AuditEvent.query.filter(
                AuditEvent.type == "agree_framework_variation"
            ).order_by(AuditEvent.created_at, AuditEvent.id).all()

            assert len(audit_events) == 2

            assert audit_events[0].user == "test123"
            assert audit_events[0].data["supplierId"] == 2
            assert audit_events[0].data["frameworkSlug"] == "g-cloud-8"
            assert audit_events[0].data["variationSlug"] == "toblerone"
            assert audit_events[0].data["update"] == {
                "agreedUserId": 2,
            }

            assert audit_events[1].user == "test123"
            assert audit_events[1].data["supplierId"] == 2
            assert audit_events[1].data["frameworkSlug"] == "g-cloud-8"
            assert audit_events[1].data["variationSlug"] == "banana"
            assert audit_events[1].data["update"] == {
                "agreedUserId": 2,
            }
