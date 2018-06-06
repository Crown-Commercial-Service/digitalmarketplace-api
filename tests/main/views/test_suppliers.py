from datetime import datetime

from flask import json
from freezegun import freeze_time
import pytest

from app import db
from app.models import Supplier, ContactInformation, AuditEvent, \
    SupplierFramework, Framework, FrameworkAgreement, DraftService, Service
from tests.bases import BaseApplicationTest, JSONTestMixin, JSONUpdateTestMixin
from tests.helpers import fixture_params, FixtureMixin, load_example_listing


class TestGetSupplier(BaseApplicationTest, FixtureMixin):
    supplier = supplier_id = None

    def setup(self):
        super(TestGetSupplier, self).setup()

        payload = load_example_listing("supplier_creation")
        self.supplier = payload

        response = self.client.post(
            '/suppliers',
            data=json.dumps({
                'suppliers': self.supplier
            }),
            content_type='application/json')
        assert response.status_code == 201
        self.supplier_id = json.loads(response.get_data())['suppliers']['id']

    def test_get_non_existent_supplier(self):
        response = self.client.get('/suppliers/100')
        assert response.status_code == 404

    def test_invalid_supplier_id(self):
        response = self.client.get('/suppliers/abc123')
        assert response.status_code == 404

    def test_get_supplier(self):
        response = self.client.get('/suppliers/{}'.format(self.supplier_id))

        data = json.loads(response.get_data())
        assert response.status_code == 200
        assert self.supplier_id == data['suppliers']['id']
        assert self.supplier['name'] == data['suppliers']['name']

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
        assert data['suppliers']['service_counts'] == {
            u'G-Cloud 5': 15,
            u'G-Cloud 6': 5
        }


class TestListSuppliers(BaseApplicationTest, FixtureMixin):
    def setup(self):
        super(TestListSuppliers, self).setup()

        # Supplier names look like "Supplier {n}"
        self.setup_dummy_suppliers(7)

    def test_query_string_missing(self):
        response = self.client.get('/suppliers')
        assert response.status_code == 200

    def test_query_string_prefix_empty(self):
        response = self.client.get('/suppliers?prefix=')
        assert response.status_code == 200

    def test_query_string_prefix_returns_none(self):
        response = self.client.get('/suppliers?prefix=canada')
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert len(data['suppliers']) == 0

    def test_other_prefix_returns_non_alphanumeric_suppliers(self):
        db.session.add(
            Supplier(supplier_id=999, name=u"999 Supplier")
        )
        self.setup_dummy_service(service_id='1230000000', supplier_id=999)

        response = self.client.get('/suppliers?prefix=other')

        data = json.loads(response.get_data())
        assert response.status_code == 200
        assert len(data['suppliers']) == 1
        assert data['suppliers'][0]['id'] == 999
        assert u"999 Supplier" == data['suppliers'][0]['name']

    def test_query_string_prefix_returns_paginated_page_one(self):
        response = self.client.get('/suppliers?prefix=s')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['suppliers']) == 5
        next_link = data['links']['next']
        assert 'page=2' in next_link

    def test_query_string_prefix_returns_paginated_page_two(self):
        response = self.client.get('/suppliers?prefix=s&page=2')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['suppliers']) == 2
        prev_link = data['links']['prev']
        assert 'page=1' in prev_link

    def test_query_string_prefix_returns_no_pagination_for_single_page(self):
        self.setup_additional_dummy_suppliers(5, 'T')
        response = self.client.get('/suppliers?prefix=t')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['suppliers']) == 5
        assert ['self'] == list(data['links'].keys())

    def test_query_string_prefix_page_out_of_range(self):
        response = self.client.get('/suppliers?prefix=s&page=10')

        assert response.status_code == 404

    def test_query_string_prefix_invalid_page_argument(self):
        response = self.client.get('/suppliers?prefix=s&page=a')

        assert response.status_code == 400

    def test_below_one_page_number_is_404(self):
        response = self.client.get('/suppliers?page=0')

        assert response.status_code == 404


class TestListSuppliersOnFramework(BaseApplicationTest, FixtureMixin):

    def setup(self):
        super(TestListSuppliersOnFramework, self).setup()

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

    def test_invalid_framework_returns_400(self):
        response = self.client.get('/suppliers?framework=invalid!')
        assert response.status_code == 400

    def test_should_return_suppliers_on_framework_backwards_compatibility(self):
        # TODO: REMOVE WHEN BUYER APP IS UPDATED
        response = self.client.get('/suppliers?framework=gcloud')
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert len(data['suppliers']) == 1
        assert data['suppliers'][0]['name'] == 'Active'

    def test_should_return_suppliers_on_framework(self):
        response = self.client.get('/suppliers?framework=g-cloud')
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert len(data['suppliers']) == 1
        assert data['suppliers'][0]['name'] == 'Active'

    def test_should_return_no_suppliers_no_framework(self):
        response = self.client.get('/suppliers?framework=bad')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['suppliers']) == 0

    def test_should_return_all_suppliers_if_no_framework(self):
        response = self.client.get('/suppliers')
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert len(data['suppliers']) == 3


class TestListSuppliersByDunsNumber(BaseApplicationTest):

    def setup(self):
        super(TestListSuppliersByDunsNumber, self).setup()

        db.session.add(
            Supplier(supplier_id=1, name=u"Duns 123", duns_number="123")
        )
        db.session.add(
            Supplier(supplier_id=2, name=u"Duns xyq", duns_number="xyz")
        )
        db.session.commit()

    def test_invalid_duns_number_returns_400(self):
        response = self.client.get('/suppliers?duns_number=invalid!')
        assert response.status_code == 400

    def test_should_return_suppliers_by_duns_number(self):
        response = self.client.get('/suppliers?duns_number=123')
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert len(data['suppliers']) == 1
        assert data['suppliers'][0]['name'] == 'Duns 123'

    def test_should_return_no_suppliers_if_nonexisting_duns(self):
        response = self.client.get('/suppliers?duns_number=not-existing')
        data = json.loads(response.get_data())
        assert response.status_code == 200
        assert len(data['suppliers']) == 0

    def test_should_return_all_suppliers_if_no_duns_number(self):
        response = self.client.get('/suppliers')
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert len(data['suppliers']) == 2


class TestPutSupplier(BaseApplicationTest, JSONTestMixin):
    method = "put"
    endpoint = "/suppliers/{self.supplier_id}"
    supplier = supplier_id = None

    def setup(self):
        super(TestPutSupplier, self).setup()
        self.supplier = load_example_listing("Supplier")
        self.supplier_id = self.supplier['id']

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
        response = self.put_import_supplier(self.supplier)
        assert response.status_code == 201
        supplier = Supplier.query.filter(
            Supplier.supplier_id == self.supplier_id
        ).first()
        assert supplier.name == self.supplier['name']

    def test_reinserting_the_same_supplier(self):
        example_listing_contact_information = self.supplier['contactInformation']

        # Exact loop number is arbitrary
        for i in range(3):
            response = self.put_import_supplier(self.supplier)

            assert response.status_code == 201

            supplier = Supplier.query.filter(
                Supplier.supplier_id == self.supplier_id
            ).first()
            assert supplier.name == self.supplier['name']

            contact_informations = ContactInformation.query.filter(
                ContactInformation.supplier_id == supplier.supplier_id
            ).all()

            assert len(example_listing_contact_information) == len(contact_informations)

            # Contact Information without a supplier_id should not exist
            contact_informations_no_supplier_id = \
                ContactInformation.query.filter(
                    ContactInformation.supplier_id == None  # noqa
                ).all()

            assert len(contact_informations_no_supplier_id) == 0

    def test_cannot_put_to_root_suppliers_url(self):
        response = self.put_import_supplier(self.supplier, "")
        assert response.status_code == 405

    def test_supplier_json_id_does_not_match_route_id_parameter(self):
        response = self.put_import_supplier(self.supplier, '/1234567890')
        assert response.status_code == 400
        assert 'id parameter must match id in data' in json.loads(response.get_data())['error']

    def test_when_supplier_has_missing_contact_information(self):
        self.supplier.pop('contactInformation')

        response = self.put_import_supplier(self.supplier)
        assert response.status_code == 400
        for item in ['Invalid JSON must have', '\'contactInformation\'']:
            assert item in json.loads(response.get_data())['error']

    def test_when_supplier_has_malformed_contact_information(self):
        self.supplier['contactInformation'] = {'wobble': 'woo'}

        response = self.put_import_supplier(self.supplier)
        assert response.status_code == 400
        for item in ['JSON was not a valid format', 'is not of type', 'array']:
            assert item in json.loads(response.get_data())['error']

    def test_when_supplier_has_a_missing_key(self):
        self.supplier.pop('id')

        response = self.put_import_supplier(self.supplier)
        assert response.status_code == 400
        for item in ['JSON was not a valid format', '\'id\'', 'is a required property']:
            assert item in json.loads(response.get_data())['error']

    def test_when_supplier_has_missing_keys(self):
        # only one key is returned in the error message
        self.supplier.pop('id')
        self.supplier.pop('name')

        response = self.put_import_supplier(self.supplier)
        assert response.status_code == 400
        for item in ['JSON was not a valid format', '\'id\'', 'is a required property']:
            assert item in json.loads(response.get_data())['error']

    def test_when_supplier_contact_information_has_a_missing_key(self):
        self.supplier['contactInformation'][0].pop('email')

        response = self.put_import_supplier(self.supplier)
        assert response.status_code == 400
        for item in ['JSON was not a valid format', '\'email\'', 'is a required property']:
            assert item in json.loads(response.get_data())['error']

    def test_when_supplier_contact_information_has_missing_keys(self):
        # only one key is returned in the error message
        self.supplier['contactInformation'][0].pop('email')
        self.supplier['contactInformation'][0].pop('contactName')

        response = self.put_import_supplier(self.supplier)
        assert response.status_code == 400
        for item in ['JSON was not a valid format', '\'contactName\'', 'is a required property']:
            assert item in json.loads(response.get_data())['error']

    def test_when_supplier_has_extra_keys(self):
        self.supplier.update({'newKey': 1})

        response = self.put_import_supplier(self.supplier)
        assert response.status_code == 400
        assert 'Additional properties are not allowed' in json.loads(response.get_data())['error']

    def test_when_supplier_contact_information_has_extra_keys(self):
        self.supplier['contactInformation'][0].update({'newKey': 1})

        response = self.put_import_supplier(self.supplier)
        assert response.status_code == 400
        assert 'Additional properties are not allowed' in json.loads(response.get_data())['error']

    def test_supplier_duns_number_invalid(self):
        self.supplier.update({'dunsNumber': "only-digits-permitted"})

        response = self.put_import_supplier(self.supplier)
        assert response.status_code == 400
        for item in ['only-digits-permitted', 'does not match']:
            assert item in json.loads(response.get_data())['error']

    def test_when_supplier_contact_information_email_invalid(self):
        self.supplier['contactInformation'][0].update({'email': "bad-email-99"})

        response = self.put_import_supplier(self.supplier)
        assert response.status_code == 400
        for item in ['bad-email-99', 'is not a']:
            assert item in json.loads(response.get_data())['error']


class TestUpdateSupplier(BaseApplicationTest, JSONUpdateTestMixin):
    method = "post"
    endpoint = "/suppliers/{self.supplier_id}"
    supplier = supplier_id = None

    def setup(self):
        super(TestUpdateSupplier, self).setup()

        payload = load_example_listing("supplier_creation")
        self.supplier = payload

        response = self.client.post(
            '/suppliers',
            data=json.dumps({'suppliers': self.supplier}),
            content_type='application/json')
        assert response.status_code == 201
        self.supplier_id = json.loads(response.get_data())['suppliers']['id']

    def update_request(self, data=None, user=None, full_data=None):
        return self.client.post(
            '/suppliers/{}'.format(self.supplier_id),
            data=json.dumps({
                'suppliers': data,
                'updated_by': user or 'supplier@user.dmdev',
            } if full_data is None else full_data),
            content_type='application/json',
        )

    def test_empty_update_supplier(self):
        response = self.update_request({})
        assert response.status_code == 200

    def test_name_update(self):
        response = self.update_request({'name': "New Name"})
        assert response.status_code == 200

        supplier = Supplier.query.filter(
            Supplier.supplier_id == self.supplier_id
        ).first()

        assert supplier.name == "New Name"

    def test_supplier_update_creates_audit_event(self):
        self.update_request({'name': "Name"})

        supplier = Supplier.query.filter(
            Supplier.supplier_id == self.supplier_id
        ).first()

        audit = AuditEvent.query.filter(
            AuditEvent.object == supplier,
            AuditEvent.type == "supplier_update"
        ).first()

        assert audit.user == "supplier@user.dmdev"
        assert audit.data == {
            'update': {'name': "Name"},
            'supplierId': supplier.supplier_id,
        }

    def test_update_response_matches_payload_plus_defaults(self):
        payload = load_example_listing("supplier_creation")
        response = self.update_request({'name': "New Name"})
        assert response.status_code == 200

        payload.update({'name': 'New Name'})
        supplier = json.loads(response.get_data())['suppliers']

        payload.pop('contactInformation')
        supplier.pop('contactInformation')
        supplier.pop('links')
        supplier.pop('id')

        payload_with_defaults = {**payload, 'companyDetailsConfirmed': False}

        assert supplier == payload_with_defaults

    def test_update_all_fields(self):
        response = self.update_request({
            "name": "New Name",
            "description": "New Description",
            "companiesHouseNumber": "AA123456",
            "dunsNumber": "010101",
            "otherCompanyRegistrationNumber": "A11",
            "registeredName": "New Name Inc.",
            "registrationCountry": "country:GT",
            "vatNumber": "12312312",
            "organisationSize": "micro",
            "tradingStatus": "sole trader",
            "companyDetailsConfirmed": True,
        })

        assert response.status_code == 200

        supplier = Supplier.query.filter(
            Supplier.supplier_id == self.supplier_id
        ).first()

        assert supplier.name == 'New Name'
        assert supplier.description == "New Description"
        assert supplier.duns_number == "010101"
        assert supplier.companies_house_number == "AA123456"
        assert supplier.other_company_registration_number == "A11"
        assert supplier.registered_name == "New Name Inc."
        assert supplier.registration_country == "country:GT"
        assert supplier.vat_number == "12312312"
        assert supplier.organisation_size == "micro"
        assert supplier.trading_status == "sole trader"
        assert supplier.company_details_confirmed is True

    def test_supplier_json_id_does_not_match_original_id(self):
        response = self.update_request({
            'id': self.supplier_id + 1,
            'name': "New Name"
        })

        assert response.status_code == 400

    def test_update_missing_supplier(self):
        response = self.client.post(
            '/suppliers/234567',
            data=json.dumps({'suppliers': {}}),
            content_type='application/json',
        )

        assert response.status_code == 404

    def test_links_and_contact_information_are_ignored(self):
        response = self.update_request(full_data={'suppliers': {
            'name': "New Name",
            'contactInformation': [],
            'links': [],
        }, 'links': [], 'updated_by': 'supplier@user.dmdev'})

        supplier = Supplier.query.filter(
            Supplier.supplier_id == self.supplier_id
        ).first()

        assert response.status_code == 200
        assert len(supplier.contact_information) == 2

    def test_update_with_unexpected_keys(self):
        response = self.update_request({
            'new_key': "value",
            'name': "New Name"
        })

        assert response.status_code == 400

    def test_update_without_updated_by(self):
        response = self.update_request(full_data={
            'suppliers': {'name': "New Name"},
        })

        assert response.status_code == 400

    def test_update_chid_with_none(self):
        response = self.update_request({"companiesHouseNumber": None})
        assert response.status_code == 200

        supplier = Supplier.query.filter(
            Supplier.supplier_id == self.supplier_id
        ).first()

        assert supplier.companies_house_number is None

    def test_update_with_bad_company_number(self):
        response = self.update_request({"companiesHouseNumber": "ABCDEFGH"})
        assert response.status_code == 400
        assert "Invalid companies house number" in response.get_data(as_text=True)

    def test_update_with_bad_company_size(self):
        response = self.update_request({"organisationSize": "tiny"})
        assert response.status_code == 400
        assert "Invalid organisation size" in response.get_data(as_text=True)

    def test_update_with_bad_trading_status(self):
        response = self.update_request({"tradingStatus": "invalid"})
        assert response.status_code == 400
        assert "Invalid trading status" in response.get_data(as_text=True)

    def test_update_succeeds_with_null_other_company_registration_number(self):
        response = self.update_request({"otherCompanyRegistrationNumber": None})
        assert response.status_code == 200

    @pytest.mark.parametrize('trading_status', filter(lambda x: x, Supplier.TRADING_STATUSES))
    def test_update_succeeds_with_valid_trading_status(self, trading_status):
        response = self.update_request({"tradingStatus": trading_status})
        assert response.status_code == 200

    def test_update_with_bad_registration_country(self):
        # Country picker data is in the format "country:gb"
        response = self.update_request({"registrationCountry": "Wales"})
        assert response.status_code == 400
        assert "Invalid registration country" in response.get_data(as_text=True)

    @pytest.mark.parametrize('country_code, expected_response',
                             (("country:GB", 200),
                              ("country:gb", 400),
                              ("country:GBA", 400),
                              ("country:AB-12", 400),
                              ("territory:AX", 200),
                              ("territory:ax", 400),
                              ("territory:GBA", 200),
                              ("territory:gba", 400),
                              ("territory:AB-12", 200),
                              ("territory:ab-12", 400),
                              ("territory:AB-CD", 200),
                              ("territory:ab-cd", 400),
                              ("territory:ABC-12", 200),
                              ("territory:AB-123", 400),
                              ("Wales", 400),
                              ))
    def test_update_with_registration_countries(self, country_code, expected_response):
        response = self.update_request({"registrationCountry": country_code})
        error_message_is_displayed = "Invalid registration country" in response.get_data(as_text=True)
        assert response.status_code == expected_response
        if expected_response == 200:
            assert not error_message_is_displayed
        else:
            assert error_message_is_displayed


class TestUpdateContactInformation(BaseApplicationTest, JSONUpdateTestMixin):
    method = "post"
    endpoint = "/suppliers/{self.supplier_id}/contact-information/{self.contact_id}"
    supplier = supplier_id = contact_id = None

    def setup(self):
        super(TestUpdateContactInformation, self).setup()

        payload = load_example_listing("supplier_creation")
        self.supplier = payload

        response = self.client.post(
            '/suppliers',
            data=json.dumps({'suppliers': self.supplier}),
            content_type='application/json')
        assert response.status_code == 201
        supplier = json.loads(response.get_data())['suppliers']
        self.supplier_id = supplier['id']
        self.contact_id = supplier['contactInformation'][0]['id']

    def update_request(self, data=None, user=None, full_data=None):
        return self.client.post(
            '/suppliers/{}/contact-information/{}'.format(self.supplier_id, self.contact_id),
            data=json.dumps({
                'contactInformation': data,
                'updated_by': user or 'supplier@user.dmdev',
            } if full_data is None else full_data),
            content_type='application/json',
        )

    def test_empty_update(self):
        response = self.update_request({})
        assert response.status_code == 200

    def test_simple_field_update(self):
        response = self.update_request({
            'city': "New City"
        })
        assert response.status_code == 200

        contact = ContactInformation.query.filter(
            ContactInformation.id == self.contact_id
        ).first()

        assert contact.city == "New City"

    def test_simple_field_update_for_supplier_with_no_companies_house_number(self):
        supplier_db = Supplier.query.first()  # Only one supplier is set up for these tests
        supplier_db.companies_house_number = None

        response = self.update_request({
            'city': "New City"
        })
        assert response.status_code == 200

        contact = ContactInformation.query.filter(
            ContactInformation.id == self.contact_id
        ).first()

        assert contact.city == "New City"

    def test_update_creates_audit_event(self):
        self.update_request({
            'city': "New City"
        })

        contact = ContactInformation.query.filter(
            ContactInformation.id == self.contact_id
        ).first()

        audit = AuditEvent.query.filter(
            AuditEvent.object == contact.supplier,
            AuditEvent.type == "contact_update"
        ).first()

        assert audit.user == "supplier@user.dmdev"
        assert audit.data == {
            'update': {'city': "New City"},
            'supplierId': contact.supplier.supplier_id,
        }

    def test_update_response_matches_payload(self):
        payload = load_example_listing("Supplier")
        response = self.update_request({
            'city': "New City"
        })
        assert response.status_code == 200

        payload = payload['contactInformation'][0]
        payload.update({'city': 'New City'})
        payload.pop('links')
        contact = json.loads(response.get_data())['contactInformation']
        contact.pop('id')
        contact.pop('links')

        assert contact == payload

    def test_update_all_fields(self):
        response = self.update_request({
            "contactName": "New contact",
            "phoneNumber": "New phone",
            "email": "new-value@example.com",
            "address1": "New address1",
            "city": "New city",
            "postcode": "New postcode",
        })

        assert response.status_code == 200

        contact = ContactInformation.query.filter(
            ContactInformation.id == self.contact_id
        ).first()

        assert contact.contact_name == "New contact"
        assert contact.phone_number == "New phone"
        assert contact.email == "new-value@example.com"
        assert contact.address1 == "New address1"
        assert contact.city == "New city"
        assert contact.postcode == "New postcode"

    def test_supplier_json_id_does_not_match_oiginal_id(self):
        response = self.update_request({
            'supplierId': 234567,
            'city': "New City"
        })

        assert response.status_code == 400

    def test_json_id_does_not_match_oiginal_id(self):
        response = self.update_request({
            'id': 2,
            'city': "New City"
        })

        assert response.status_code == 400

    def test_update_missing_supplier(self):
        response = self.client.post(
            '/suppliers/234567/contact-information/%s' % self.contact_id,
            data=json.dumps({}),
            content_type='application/json',
        )

        assert response.status_code == 404

    def test_update_missing_contact_information(self):
        response = self.client.post(
            '/suppliers/123456/contact-information/100000',
            data=json.dumps({'contactInformation': {}}),
            content_type='application/json',
        )

        assert response.status_code == 404

    def test_update_with_unexpected_keys(self):
        response = self.update_request({
            'new_key': "value",
            'city': "New City"
        })

        assert response.status_code == 400

    def test_update_ignores_links(self):
        response = self.update_request({
            'links': "value",
            'city': "New City"
        })

        assert response.status_code == 200

    def test_update_without_updated_by(self):
        response = self.update_request(full_data={
            'contactInformation': {'city': "New City"},
        })

        assert response.status_code == 400


class TestSetSupplierDeclarations(BaseApplicationTest, FixtureMixin, JSONUpdateTestMixin):
    method = 'put'
    endpoint = '/suppliers/0/frameworks/g-cloud-4/declaration'

    def setup(self):
        super(TestSetSupplierDeclarations, self).setup()
        # This is automatically removed in BaseApplicationTest.teardown
        framework = Framework(
            id=100,
            slug='test-open',
            name='Test open',
            framework='g-cloud',
            status='open',
            has_direct_award=True,
            has_further_competition=False)
        db.session.add(framework)
        db.session.commit()
        self.setup_dummy_suppliers(1)

    def test_add_new_declaration(self):
            response = self.client.put(
                '/suppliers/0/frameworks/test-open/declaration',
                data=json.dumps({
                    'updated_by': 'testing',
                    'declaration': {
                        'question': 'answer'
                    }
                }),
                content_type='application/json')

            assert response.status_code == 201
            answer = SupplierFramework \
                .find_by_supplier_and_framework(0, 'test-open').first()
            assert answer.declaration['question'] == 'answer'

    def test_add_null_declaration_should_result_in_dict(self):
        response = self.client.put(
            '/suppliers/0/frameworks/test-open/declaration',
            data=json.dumps({
                'updated_by': 'testing',
                'declaration': None
            }),
            content_type='application/json')

        assert response.status_code == 201
        answer = SupplierFramework \
            .find_by_supplier_and_framework(0, 'test-open').first()
        assert isinstance(answer.declaration, dict)

    def test_update_existing_declaration(self):
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

        assert response.status_code == 200
        supplier_framework = SupplierFramework \
            .find_by_supplier_and_framework(0, 'test-open').first()
        assert supplier_framework.declaration['question'] == 'answer2'


class TestPostSupplier(BaseApplicationTest, JSONTestMixin):
    method = "post"
    endpoint = "/suppliers"

    def setup(self):
        super(TestPostSupplier, self).setup()

    def post_supplier(self, supplier):

        return self.client.post(
            '/suppliers',
            data=json.dumps({'suppliers': supplier}),
            content_type='application/json')

    def test_add_a_new_supplier(self):
        payload = load_example_listing("new-supplier")

        response = self.post_supplier(payload)

        assert response.status_code == 201

        supplier = Supplier.query.filter(
            Supplier.name == payload['name']
        ).first()
        assert supplier is not None

        audit = AuditEvent.query.filter(
            AuditEvent.object == supplier
        ).first()
        assert audit.type == "create_supplier"
        assert audit.user == "no logged-in user"
        assert audit.data == {
            'update': payload,
            'supplierId': supplier.supplier_id,
        }

    def test_when_supplier_has_missing_contact_information(self):
        payload = load_example_listing("new-supplier")
        payload.pop('contactInformation')

        response = self.post_supplier(payload)
        assert response.status_code == 400
        for item in ['Invalid JSON must have', '\'contactInformation\'']:
            assert item in json.loads(response.get_data())['error']

    def test_when_supplier_has_malformed_contact_information(self):
        payload = load_example_listing("new-supplier")
        payload['contactInformation'] = {
            'waa': 'woo'
        }

        response = self.post_supplier(payload)
        assert response.status_code == 400
        for item in ['JSON was not a valid format',
                     'is not of type',
                     'array']:
            assert item in json.loads(response.get_data())['error']

    def test_when_supplier_has_a_missing_key(self):
        payload = load_example_listing("new-supplier")
        payload.pop('name')

        response = self.post_supplier(payload)
        assert response.status_code == 400
        for item in ['JSON was not a valid format', '\'name\'', 'is a required property']:
            assert item in json.loads(response.get_data())['error']

    def test_when_supplier_contact_information_has_a_missing_key(self):
        payload = load_example_listing("new-supplier")

        payload['contactInformation'][0].pop('email')

        response = self.post_supplier(payload)
        assert response.status_code == 400
        for item in ['JSON was not a valid format', '\'email\'', 'is a required property']:
            assert item in json.loads(response.get_data())['error']

    def test_when_supplier_has_extra_keys(self):
        payload = load_example_listing("new-supplier")

        payload.update({'newKey': 1})

        response = self.post_supplier(payload)
        assert response.status_code == 400
        assert 'Additional properties are not allowed' in json.loads(response.get_data())['error']

    def test_when_supplier_contact_information_has_extra_keys(self):
        payload = load_example_listing("new-supplier")

        payload['contactInformation'][0].update({'newKey': 1})

        response = self.post_supplier(payload)
        assert response.status_code == 400
        assert 'Additional properties are not allowed' in json.loads(response.get_data())['error']

    def test_supplier_duns_number_invalid(self):
        payload = load_example_listing("new-supplier")

        payload.update({'dunsNumber': "only-digits-permitted"})

        response = self.post_supplier(payload)
        assert response.status_code == 400
        for item in ['only-digits-permitted', 'does not match']:
            assert item in json.loads(response.get_data())['error']

    def test_supplier_companies_house_invalid(self):
        payload = load_example_listing("new-supplier")

        payload.update({'companiesHouseNumber': "longer-than-allowed"})

        response = self.post_supplier(payload)
        assert response.status_code == 400
        for item in ['longer-than-allowed', 'is too long']:
            assert item in json.loads(response.get_data())['error']

    def test_when_supplier_contact_information_email_invalid(self):
        payload = load_example_listing("new-supplier")

        payload['contactInformation'][0].update({'email': "bad-email-99"})

        response = self.post_supplier(payload)
        assert response.status_code == 400
        for item in ['bad-email-99', 'is not a']:
            assert item in json.loads(response.get_data())['error']

    def test_should_not_be_able_to_import_same_duns_number(self):
        payload1 = load_example_listing("new-supplier")
        payload2 = load_example_listing("new-supplier")

        response = self.post_supplier(payload1)
        assert response.status_code == 201
        response = self.post_supplier(payload2)
        assert response.status_code == 400
        data = json.loads(response.get_data())
        assert 'duplicate key value violates unique constraint "ix_suppliers_duns_number"' in data['error']


class TestGetSupplierFrameworks(BaseApplicationTest):
    def setup(self):
        super(TestGetSupplierFrameworks, self).setup()

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
        assert response.status_code == 200
        assert (
            data ==
            {
                'frameworkInterest': [
                    {
                        'agreementReturned': False,
                        'agreementReturnedAt': None,
                        'onFramework': False,
                        'declaration': {},
                        'frameworkSlug': 'g-cloud-6',
                        'frameworkFramework': 'g-cloud',
                        'frameworkFamily': 'g-cloud',
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
                        'prefillDeclarationFromFrameworkSlug': None,
                    }
                ]
            })

    def test_supplier_with_service(self):
        response = self.client.get('/suppliers/2/frameworks')
        data = json.loads(response.get_data())
        assert response.status_code == 200
        assert (
            data ==
            {
                'frameworkInterest': [
                    {
                        'agreementReturned': False,
                        'agreementReturnedAt': None,
                        'onFramework': False,
                        'declaration': {},
                        'frameworkSlug': 'g-cloud-6',
                        'frameworkFramework': 'g-cloud',
                        'frameworkFamily': 'g-cloud',
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
                        'prefillDeclarationFromFrameworkSlug': None,
                    }
                ]
            })

    def test_supplier_with_no_drafts_or_services(self):
        response = self.client.get('/suppliers/3/frameworks')
        data = json.loads(response.get_data())
        assert response.status_code == 200
        assert data == {'frameworkInterest': []}

    def test_supplier_that_doesnt_exist(self):
        response = self.client.get('/suppliers/4/frameworks')
        assert response.status_code == 404


class TestRegisterFrameworkInterest(BaseApplicationTest, FixtureMixin, JSONUpdateTestMixin):
    method = "put"
    endpoint = "/suppliers/1/frameworks/digital-outcomes-and-specialists"

    def setup(self):
        super(TestRegisterFrameworkInterest, self).setup()

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
        response = self.register_interest(1, 'digital-outcomes-and-specialists')

        assert response.status_code == 201
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['supplierId'] == 1
        assert data['frameworkInterest']['frameworkSlug'] == 'digital-outcomes-and-specialists'
        assert isinstance(data['frameworkInterest']['declaration'], dict)

    def test_can_not_register_interest_in_not_open_framework_(self):
        response = self.register_interest(1, 'g-cloud-5')

        assert response.status_code == 400
        data = json.loads(response.get_data())
        assert data['error'] == "'g-cloud-5' framework is not open"

    def test_can_not_register_interest_more_than_once_in_open_framework(self):
        response1 = self.register_interest(1, 'digital-outcomes-and-specialists')
        assert response1.status_code == 201
        data = json.loads(response1.get_data())
        assert data['frameworkInterest']['supplierId'] == 1
        assert data['frameworkInterest']['frameworkSlug'] == 'digital-outcomes-and-specialists'

        response2 = self.register_interest(1, 'digital-outcomes-and-specialists', user='another@example.com')
        assert response2.status_code == 200
        data = json.loads(response2.get_data())
        assert data['frameworkInterest']['supplierId'] == 1
        assert data['frameworkInterest']['frameworkSlug'] == 'digital-outcomes-and-specialists'

    def test_can_not_send_payload_to_register_interest_endpoint(self):
        response = self.client.put(
            '/suppliers/1/frameworks/digital-outcomes-and-specialists',
            data=json.dumps(
                {
                    'updated_by': 'interested@example.com',
                    'update': {'agreementReturned': True}
                }),
            content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.get_data())
        assert data['error'] == 'This PUT endpoint does not take a payload.'

    def test_register_interest_creates_audit_event(self):
        self.register_interest(1, 'digital-outcomes-and-specialists')

        supplier = Supplier.query.filter(
            Supplier.supplier_id == 1
        ).first()

        audit = AuditEvent.query.filter(
            AuditEvent.object == supplier
        ).first()

        assert audit.type == "register_framework_interest"
        assert audit.user == "interested@example.com"
        assert audit.data['supplierId'] == 1
        assert audit.data['frameworkSlug'] == 'digital-outcomes-and-specialists'

    def test_can_get_registered_frameworks_for_a_supplier(self):
        response1 = self.client.get("/suppliers/1/frameworks/interest")
        assert response1.status_code == 200
        data = json.loads(response1.get_data())
        assert data['frameworks'] == []

        self.register_interest(1, 'digital-outcomes-and-specialists')

        response2 = self.client.get("/suppliers/1/frameworks/interest")
        assert response2.status_code == 200
        data = json.loads(response2.get_data())
        assert data['frameworks'] == ['digital-outcomes-and-specialists']


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
        supplier_framework_object = SupplierFramework.find_by_supplier_and_framework(
            supplier_framework['supplierId'], supplier_framework['frameworkSlug']
        ).first()

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
            'frameworkFramework': supplier_framework['frameworkFramework'],
            'frameworkFamily': supplier_framework['frameworkFamily'],
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
            'agreedVariations': {},
            'prefillDeclarationFromFrameworkSlug': None,
        }

    def test_get_supplier_framework_returns_signed_framework_agreement(self, supplier_framework):
        supplier_framework_object = SupplierFramework.find_by_supplier_and_framework(
            supplier_framework['supplierId'], supplier_framework['frameworkSlug']
        ).first()

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
        framework_agreement_id = framework_agreement.id

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
            'frameworkFramework': supplier_framework['frameworkFramework'],
            'frameworkFamily': supplier_framework['frameworkFamily'],
            'declaration': {'an_answer': 'Yes it is'},
            'onFramework': True,
            'agreementId': framework_agreement_id,
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
            'agreedVariations': {},
            'prefillDeclarationFromFrameworkSlug': None,
        }

    def test_get_supplier_framework_returns_countersigned_framework_agreement(self, supplier_framework, supplier):
        supplier_framework_object = SupplierFramework.find_by_supplier_and_framework(
            supplier_framework['supplierId'], supplier_framework['frameworkSlug']
        ).first()

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
        framework_agreement_id = framework_agreement.id

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
            'frameworkFramework': supplier_framework['frameworkFramework'],
            'frameworkFamily': supplier_framework['frameworkFamily'],
            'declaration': {'an_answer': 'Yes it is'},
            'onFramework': True,
            'agreementId': framework_agreement_id,
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
            'agreedVariations': {},
            'prefillDeclarationFromFrameworkSlug': None,
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

    @staticmethod
    def _refetch_serialized_sf(supplier_framework):
        # must be performed within an app context
        return SupplierFramework.query.filter(
            SupplierFramework.framework.has(Framework.slug == supplier_framework["frameworkSlug"])
        ).filter(
            SupplierFramework.supplier_id == supplier_framework["supplierId"]
        ).order_by(Supplier.id.asc()).first().serialize()

    @staticmethod
    def _latest_supplier_update_audit_event(supplier_id):
        # must be performed within an app context
        return AuditEvent.query.filter(
            AuditEvent.object == Supplier.query.filter(
                Supplier.supplier_id == supplier_id
            ).first(),
            AuditEvent.type == "update_supplier_framework",
        ).order_by(AuditEvent.created_at.desc()).first()

    @classmethod
    def _assert_and_return_audit_event(cls, supplier_framework):
        # must be performed within an app context
        audit = cls._latest_supplier_update_audit_event(supplier_framework['supplierId'])
        assert audit.type == "update_supplier_framework"
        assert audit.user == "interested@example.com"
        assert audit.data['supplierId'] == supplier_framework['supplierId']
        assert audit.data['frameworkSlug'] == supplier_framework['frameworkSlug']
        # we also return the audit object as the caller will probably want to do some test-specific assertions
        # of its own
        return audit

    def test_adding_supplier_has_passed_then_failed(self, supplier_framework):
        response = self.supplier_framework_interest(
            supplier_framework,
            update={'onFramework': True}
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['supplierId'] == supplier_framework['supplierId']
        assert data['frameworkInterest']['frameworkSlug'] == supplier_framework['frameworkSlug']
        assert data['frameworkInterest']['onFramework'] is True
        assert data['frameworkInterest']['agreementReturned'] is False

        assert data['frameworkInterest'] == self._refetch_serialized_sf(data['frameworkInterest'])
        audit = self._assert_and_return_audit_event(supplier_framework)
        assert audit.data['update']['onFramework'] is True

        response2 = self.supplier_framework_interest(
            supplier_framework,
            update={'onFramework': False}
        )
        assert response2.status_code == 200
        data = json.loads(response2.get_data())
        assert data['frameworkInterest']['supplierId'] == supplier_framework['supplierId']
        assert data['frameworkInterest']['frameworkSlug'] == supplier_framework['frameworkSlug']
        assert data['frameworkInterest']['onFramework'] is False
        assert data['frameworkInterest']['agreementReturned'] is False

        assert data['frameworkInterest'] == self._refetch_serialized_sf(data['frameworkInterest'])
        audit = self._assert_and_return_audit_event(supplier_framework)
        assert audit.data['update']['onFramework'] is False

    def test_adding_supplier_has_failed_then_passed(self, supplier_framework):
        response = self.supplier_framework_interest(
            supplier_framework,
            update={'onFramework': False}
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['supplierId'] == supplier_framework['supplierId']
        assert data['frameworkInterest']['frameworkSlug'] == supplier_framework['frameworkSlug']
        assert data['frameworkInterest']['onFramework'] is False
        assert data['frameworkInterest']['agreementReturned'] is False

        assert data['frameworkInterest'] == self._refetch_serialized_sf(data['frameworkInterest'])
        audit = self._assert_and_return_audit_event(supplier_framework)
        assert audit.data['update']['onFramework'] is False

        response2 = self.supplier_framework_interest(
            supplier_framework,
            update={'onFramework': True}
        )
        assert response2.status_code == 200
        data = json.loads(response2.get_data())
        assert data['frameworkInterest']['supplierId'] == supplier_framework['supplierId']
        assert data['frameworkInterest']['frameworkSlug'] == supplier_framework['frameworkSlug']
        assert data['frameworkInterest']['onFramework'] is True
        assert data['frameworkInterest']['agreementReturned'] is False

        assert data['frameworkInterest'] == self._refetch_serialized_sf(data['frameworkInterest'])
        audit = self._assert_and_return_audit_event(supplier_framework)
        assert audit.data['update']['onFramework'] is True

    def test_can_only_update_whitelisted_properties_with_this_route(self, supplier_framework):
        response = self.supplier_framework_interest(
            supplier_framework,
            update={'onFramework': True, 'agreementReturned': True}
        )
        assert response.status_code == 400
        error_message = json.loads(response.get_data(as_text=True))['error']
        assert error_message == "Invalid JSON should not have 'agreementReturned' keys"

        # check nothing has changed on db
        assert supplier_framework == self._refetch_serialized_sf(supplier_framework)
        assert self._latest_supplier_update_audit_event(supplier_framework["supplierId"]) is None

    def test_setting_unsetting_prefill_declaration_from_framework_happy_path(
        self,
        open_g8_framework_live_dos_framework_suppliers_on_framework,
    ):
        supplier_framework = SupplierFramework.query.filter(
            SupplierFramework.framework.has(Framework.slug == "digital-outcomes-and-specialists")
        ).order_by(Supplier.id.asc()).first().serialize()

        response = self.supplier_framework_interest(
            supplier_framework,
            update={'prefillDeclarationFromFrameworkSlug': "g-cloud-8"}
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['supplierId'] == supplier_framework['supplierId']
        assert data['frameworkInterest']['frameworkSlug'] == supplier_framework['frameworkSlug']
        assert data['frameworkInterest']['prefillDeclarationFromFrameworkSlug'] == "g-cloud-8"

        assert data['frameworkInterest'] == self._refetch_serialized_sf(data['frameworkInterest'])
        audit = self._assert_and_return_audit_event(supplier_framework)
        assert audit.data['update']['prefillDeclarationFromFrameworkSlug'] == "g-cloud-8"

        response = self.supplier_framework_interest(
            supplier_framework,
            update={'prefillDeclarationFromFrameworkSlug': None},
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['supplierId'] == supplier_framework['supplierId']
        assert data['frameworkInterest']['frameworkSlug'] == supplier_framework['frameworkSlug']
        assert data['frameworkInterest']['prefillDeclarationFromFrameworkSlug'] is None

        assert data['frameworkInterest'] == self._refetch_serialized_sf(data['frameworkInterest'])
        audit = self._assert_and_return_audit_event(supplier_framework)
        assert audit.data['update']['prefillDeclarationFromFrameworkSlug'] is None

    def test_setting_prefill_declaration_from_framework_invalid_framework_slug(
        self,
        open_g8_framework_live_dos_framework_suppliers_on_framework,
    ):
        supplier_framework = SupplierFramework.query.filter(
            SupplierFramework.framework.has(Framework.slug == "digital-outcomes-and-specialists")
        ).order_by(Supplier.id.asc()).first().serialize()

        response = self.supplier_framework_interest(
            supplier_framework,
            update={'prefillDeclarationFromFrameworkSlug': "metempsychosis"}
        )
        assert response.status_code == 400

        # check nothing has changed on db
        assert supplier_framework == self._refetch_serialized_sf(supplier_framework)
        assert self._latest_supplier_update_audit_event(supplier_framework["supplierId"]) is None

    def test_multiple_simultaneous_property_updates(
        self,
        open_g8_framework_live_dos_framework_suppliers_on_framework,
    ):
        supplier_framework = SupplierFramework.query.filter(
            SupplierFramework.framework.has(Framework.slug == "digital-outcomes-and-specialists")
        ).order_by(Supplier.id.asc()).first().serialize()

        response = self.supplier_framework_interest(
            supplier_framework,
            update={
                "prefillDeclarationFromFrameworkSlug": "g-cloud-8",
                "onFramework": False,
            },
        )
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['frameworkInterest']['supplierId'] == supplier_framework['supplierId']
        assert data['frameworkInterest']['frameworkSlug'] == supplier_framework['frameworkSlug']
        assert data['frameworkInterest']['prefillDeclarationFromFrameworkSlug'] == "g-cloud-8"

        supplier_framework2 = self._refetch_serialized_sf(data['frameworkInterest'])
        assert data['frameworkInterest'] == supplier_framework2
        audit = self._assert_and_return_audit_event(supplier_framework)
        audit_id = audit.id
        assert audit.data['update']['prefillDeclarationFromFrameworkSlug'] == "g-cloud-8"

        # now we make sure that a single property update failure prevents any db changes
        response2 = self.supplier_framework_interest(
            supplier_framework,
            update={
                "prefillDeclarationFromFrameworkSlug": "met-him-pike-hoses",
                "onFramework": True,
            },
        )
        assert response2.status_code == 400

        # check nothing has changed on db
        assert supplier_framework2 == self._refetch_serialized_sf(supplier_framework2)
        assert self._latest_supplier_update_audit_event(supplier_framework2["supplierId"]).id == audit_id

    def test_setting_prefill_declaration_from_framework_supplier_not_on_other_framework(
        self,
        open_g8_framework_live_dos_framework_suppliers_dos_sf,
    ):
        supplier_framework = SupplierFramework.query.filter(
            SupplierFramework.framework.has(Framework.slug == "digital-outcomes-and-specialists")
        ).order_by(Supplier.id.asc()).first().serialize()

        response = self.supplier_framework_interest(
            supplier_framework,
            update={'prefillDeclarationFromFrameworkSlug': "g-cloud-8"}
        )
        assert response.status_code == 400

        # check nothing has changed on db
        assert supplier_framework == self._refetch_serialized_sf(supplier_framework)
        assert self._latest_supplier_update_audit_event(supplier_framework["supplierId"]) is None


class TestSupplierFrameworkVariation(BaseApplicationTest, FixtureMixin):
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
        self, live_g8_framework_2_variations_suppliers_not_on_framework
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
            "agreedAt": "2016-06-06T00:00:00.000000Z",
        }
        expected_variation_with_user = dict(
            expected_variation,
            agreedUserEmail="test+1@digital.gov.uk",
            agreedUserName="my name",
        )

        assert response.status_code == 200
        response_json = json.loads(response.get_data())
        assert response_json["agreedVariations"] == expected_variation

        response2 = self.client.get("/suppliers/1/frameworks/g-cloud-8")
        assert response2.status_code == 200
        assert json.loads(response2.get_data())["frameworkInterest"]["agreedVariations"] == {
            "banana": expected_variation_with_user,
        }

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
            "agreedAt": "2016-06-06T00:00:00.000000Z",
        }
        expected_variation_toblerone_with_user = dict(
            expected_variation_toblerone,
            agreedUserEmail="test+2@digital.gov.uk",
            agreedUserName="my name",
        )

        assert response.status_code == 200
        response_json = json.loads(response.get_data())
        assert response_json["agreedVariations"] == expected_variation_toblerone

        response2 = self.client.get("/suppliers/2/frameworks/g-cloud-8")
        assert response2.status_code == 200
        assert json.loads(response2.get_data())["frameworkInterest"]["agreedVariations"] == {
            "toblerone": expected_variation_toblerone_with_user,
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
            "agreedAt": "2016-07-07T00:00:00.000000Z",
        }
        expected_variation_banana_with_user = dict(
            expected_variation_banana,
            agreedUserEmail="test+2@digital.gov.uk",
            agreedUserName="my name",
        )

        assert response4.status_code == 200
        response4_json = json.loads(response4.get_data())
        assert response4_json["agreedVariations"] == expected_variation_banana

        response5 = self.client.get("/suppliers/2/frameworks/g-cloud-8")
        assert response5.status_code == 200
        assert json.loads(response5.get_data())["frameworkInterest"]["agreedVariations"] == {
            "banana": expected_variation_banana_with_user,
            "toblerone": expected_variation_toblerone_with_user,
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
            "banana": expected_variation_banana_with_user,
            "toblerone": expected_variation_toblerone_with_user,
        }

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


class TestSuppliersExport(BaseApplicationTest, FixtureMixin):

    framework_slug = None
    updater_json = None

    def setup(self):
        super(TestSuppliersExport, self).setup()
        self.setup_default_buyer_domain()
        self.framework_slug = 'digital-outcomes-and-specialists'
        self.set_framework_status(self.framework_slug, 'open')
        self.updater_json = {'updated_by': 'Paula'}

    def _set_framework_status(self, status='pending'):
        self.set_framework_status(self.framework_slug, status)

    def _return_suppliers_export(self):
        response = self.client.get('/suppliers/export/{}'.format(self.framework_slug))
        assert response.status_code == 200
        return response

    def _return_suppliers_export_after_setting_framework_status(self, status='pending'):
        self._set_framework_status(status)
        return self._return_suppliers_export()

    def _register_supplier_with_framework(self):
        response = self.client.put(
            '/suppliers/{}/frameworks/{}'.format(self.supplier_id, self.framework_slug),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert response.status_code == 201

    def _setup_supplier_on_framework(self, post_supplier=True, register_supplier_with_framework=True):
        if post_supplier:
            # set the supplier_id to the id of the last supplier created
            self.supplier_id = self.setup_dummy_suppliers(2)[-1]
        if register_supplier_with_framework:
            self._register_supplier_with_framework()

    def _post_complete_draft_service(self):
        payload = load_example_listing("DOS-digital-specialist")

        self.draft_json = {'services': payload}
        self.draft_json['services']['supplierId'] = self.supplier_id
        self.draft_json['services']['frameworkSlug'] = self.framework_slug
        self.draft_json.update(self.updater_json)

        response = self.client.post(
            '/draft-services',
            data=json.dumps(self.draft_json),
            content_type='application/json')

        assert response.status_code == 201

        draft_id = json.loads(response.get_data())['services']['id']
        complete = self.client.post(
            '/draft-services/{}/complete'.format(draft_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert complete.status_code == 200

    def _put_declaration(self, status):
        data = {'declaration': {'status': status}}
        data.update(self.updater_json)

        response = self.client.put(
            '/suppliers/{}/frameworks/{}/declaration'.format(self.supplier_id, self.framework_slug),
            data=json.dumps(data),
            content_type='application/json')

        assert response.status_code == 201

    def _put_complete_declaration(self):
        self._put_declaration(status='complete')

    def _put_incomplete_declaration(self):
        self._put_declaration(status='started')

    def test_get_response_when_no_suppliers(self):
        data = json.loads(self._return_suppliers_export_after_setting_framework_status().get_data())["suppliers"]
        assert data == []

    def test_400_response_if_bad_framework_name(self):
        self._setup_supplier_on_framework()
        response = self.client.get('/suppliers/export/{}'.format('cyber-outcomes-and-cyber-specialists'))
        assert response.status_code == 400

    def test_400_response_if_framework_is_coming(self):
        self._setup_supplier_on_framework()
        self._set_framework_status('coming')
        response = self.client.get('/suppliers/export/{}'.format(self.framework_slug))
        assert response.status_code == 400

    def test_get_response_when_not_registered_with_framework(self):
        self._setup_supplier_on_framework(register_supplier_with_framework=False)
        data = json.loads(self._return_suppliers_export_after_setting_framework_status().get_data())["suppliers"]
        assert data == []

    def test_response_unstarted_declaration_no_drafts(self):
        self._setup_supplier_on_framework()
        data = json.loads(self._return_suppliers_export_after_setting_framework_status().get_data())["suppliers"]

        assert data == [
            {
                'supplier_id': 1,
                'application_result': 'no result',
                'application_status': 'no_application',
                'declaration_status': 'unstarted',
                'framework_agreement': False,
                'supplier_name': "Supplier 1",
                'supplier_organisation_size': "small",
                'duns_number': "100000001",
                'registered_name': 'Registered Supplier Name 1',
                'companies_house_number': None,
                "published_services_count": {
                    "digital-outcomes": 0,
                    "digital-specialists": 0,
                    "user-research-studios": 0,
                    "user-research-participants": 0,
                },
                "contact_information": {
                    'contact_name': 'Contact for Supplier 1',
                    'contact_email': '1@contact.com',
                    'contact_phone_number': None,
                    'address_first_line': '7 Gem Lane',
                    'address_city': 'Cantelot',
                    'address_postcode': 'CN1A 1AA',
                    'address_country': 'country:GB',
                },
                'variations_agreed': '',
            }
        ]

    def test_response_unstarted_declaration_one_draft(self):
        self._setup_supplier_on_framework()
        self._post_complete_draft_service()
        data = json.loads(self._return_suppliers_export_after_setting_framework_status().get_data())["suppliers"]
        assert data[0]["published_services_count"] == {
            "digital-outcomes": 0,
            "digital-specialists": 0,
            "user-research-studios": 0,
            "user-research-participants": 0
        }


    def test_response_started_declaration_one_draft(self):
        self._setup_supplier_on_framework()
        self._put_incomplete_declaration()
        self._post_complete_draft_service()
        data = json.loads(self._return_suppliers_export_after_setting_framework_status().get_data())["suppliers"]
        assert data[0]['declaration_status'] == 'started'
