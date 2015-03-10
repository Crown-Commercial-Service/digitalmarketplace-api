from flask import json
from nose.tools import assert_equal, assert_in, assert_not_equal, \
    assert_almost_equal

from app import db
from app.models import Service, Supplier
from datetime import datetime, timedelta
from .helpers import BaseApplicationTest, JSONUpdateTestMixin


class TestListServices(BaseApplicationTest):
    def test_list_services_with_no_services(self):
        response = self.client.get('/services')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(data['services'], [])

    def test_list_services(self):
        self.setup_dummy_services(1)
        response = self.client.get('/services')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 1)

    def test_list_services_returns_supplier_info(self):
        self.setup_dummy_services(1)
        response = self.client.get('/services')
        data = json.loads(response.get_data())
        service = data['services'][0]

        assert_equal(service['supplierId'], 0)
        assert_equal(service['supplierName'], u'Supplier 0')

    def test_paginated_list_services_page_one(self):
        self.setup_dummy_services(150)

        response = self.client.get('/services')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 100)
        next_link = first_by_rel('next', data['links'])
        assert_in("page=2", next_link['href'])

    def test_paginated_list_services_page_two(self):
        self.setup_dummy_services(150)

        response = self.client.get('/services?page=2')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 50)
        prev_link = first_by_rel('prev', data['links'])
        assert_in("page=1", prev_link['href'])

    def test_paginated_list_services_page_out_of_range(self):
        self.setup_dummy_services(15)

        response = self.client.get('/services?page=10')

        # TODO: decide whether this is actually correct.
        # this is what Flask-SQLAlchemy does by default so is easy
        assert_equal(response.status_code, 404)

    def test_x_forwarded_proto(self):
        self.setup_dummy_services(1)

        response = self.client.get('/services',
                                   headers={'X-Forwarded-Proto': 'https'})
        data = json.loads(response.get_data())

        assert data['services'][0]['links'][0]['href'].startswith('https://')

    def test_invalid_page_argument(self):
        response = self.client.get('/services?page=a')

        assert_equal(response.status_code, 400)

    def test_invalid_supplier_id_argument(self):
        response = self.client.get('/services?supplier_id=a')

        assert_equal(response.status_code, 400)

    def test_supplier_id_filter(self):
        self.setup_dummy_services(15)

        response = self.client.get('/services?supplier_id=1')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(
            list(filter(lambda s: s['supplierId'] == 1, data['services'])),
            data['services']
        )

    def test_supplier_id_filter_pagination(self):
        self.setup_dummy_services(450)

        response = self.client.get('/services?supplier_id=1&page=2')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 50)
        assert_equal(
            list(filter(lambda s: s['supplierId'] == 1, data['services'])),
            data['services']
        )

    def test_supplier_id_filter_pagination_links(self):
        self.setup_dummy_services(450)

        response = self.client.get('/services?supplier_id=1&page=1')
        data = json.loads(response.get_data())

        next_link = first_by_rel('next', data['links'])
        assert_in("page=2", next_link['href'])
        assert_in("supplier_id=1", next_link['href'])

    def test_unknown_supplier_id(self):
        self.setup_dummy_services(15)
        response = self.client.get('/services?supplier_id=100')

        assert_equal(response.status_code, 404)


def first_by_rel(rel, links):
    for link in links:
        if link['rel'] == rel:
            return link


# todo: mixin standard JSON tests
class TestPostService(BaseApplicationTest):
    def setup(self):
        super(TestPostService, self).setup()
        now = datetime.now()
        payload = self.load_example_listing("SSP-JSON-IaaS")
        with self.app.app_context():
            db.session.add(
                Supplier(supplier_id=1, name=u"Supplier 1")
            )

    def test_can_not_post_to_root_services_url(self):
        response = self.client.post(
            "/services",
            data=json.dumps(
                {'update_details': {
                    'updated_by': 'joeblogs',
                    'update_reason': 'whateves'},
                 'services': {
                     'serviceName': 'new service name'}}),
            content_type='application/json')

        assert_equal(response.status_code, 405)

    def test_returns_404_if_no_service_found(self):
        response = self.client.post(
            "/services/99999",
            data=json.dumps(
                {'update_details': {
                    'updated_by': 'joeblogs',
                    'update_reason': 'whateves'},
                 'services': {
                     'serviceName': 'new service name'}}),
            content_type='application/json')

        assert_equal(response.status_code, 404)

    def test_can_not_update_without_updater_details(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-IaaS")
            service_id = str(payload['id'])
            response = self.client.put(
                '/services/%s' % service_id,
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 201)
            response = self.client.post(
                '/services/%s' % service_id,
                data=json.dumps(
                    {'services': {
                        'serviceName': 'new service name'}}),
                content_type='application/json')

            data = json.loads(response.get_data())
            assert_equal(data['error'],
                         "Invalid JSON must have a 'update_details' key")
            assert_equal(response.status_code, 400)

    def test_can_post_a_valid_service_update(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-IaaS")
            service_id = str(payload['id'])
            response = self.client.put(
                '/services/%s' % service_id,
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 201)

        response = self.client.post(
            '/services/%s' % service_id,
            data=json.dumps(
                {'update_details': {
                    'updated_by': 'joeblogs',
                    'update_reason': 'whateves'},
                 'services': {
                     'serviceName': 'new service name'}}),
            content_type='application/json')

        assert_equal(response.status_code, 200)

        response = self.client.get('/services/%s' % service_id)

        data = json.loads(response.get_data())
        assert_equal(data['services']['serviceName'], 'new service name')
        assert_equal(response.status_code, 200)

    def test_can_post_a_valid_service_update_with_list(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-IaaS")
            service_id = str(payload['id'])
            response = self.client.put(
                '/services/%s' % service_id,
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 201)

            support_types = ['Service desk', 'Email',
                             'Phone', 'Live chat', 'Onsite']
            response = self.client.post(
                '/services/%s' % service_id,
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'supportTypes': support_types}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.get('/services/%s' % service_id)
            data = json.loads(response.get_data())

            assert_equal(all(i in support_types for i in
                             data['services']['supportTypes']), True)
            assert_equal(response.status_code, 200)

    def test_can_post_a_valid_service_update_with_object(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-IaaS")
            service_id = str(payload['id'])
            response = self.client.put(
                '/services/%s' % service_id,
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 201)

            identity_authentication_controls = {
                "value": [
                    "Authentication federation"
                ],
                "assurance": "CESG-assured components"
            }

            response = self.client.post(
                '/services/%s' % service_id,
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'identityAuthenticationControls':
                             identity_authentication_controls}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.get('/services/%s' % service_id)
            data = json.loads(response.get_data())

            updated_auth_controls = \
                data['services']['identityAuthenticationControls']
            assert_equal(response.status_code, 200)
            assert_equal(updated_auth_controls['assurance'],
                         'CESG-assured components')
            assert_equal(len(updated_auth_controls['value']), 1)
            assert_equal('Authentication federation' in
                         updated_auth_controls['value'], True)

    def test_invalid_field_not_accepted_on_update_for_iaas(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-IaaS")
            response = self.client.put(
                '/services/' + str(payload['id']),
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 201)

            response = self.client.post(
                "/services/" + str(payload['id']),
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'this is invalid': 'so I should never see this'}}),
                content_type='application/json')

            assert_equal(json.loads(
                response.get_data())['error'], 'JSON was not a valid format')
            assert_equal(response.status_code, 400)

    def test_invalid_field_not_accepted_on_update_for_saas(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-SaaS")
            response = self.client.put(
                '/services/' + str(payload['id']),
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 201)

            response = self.client.post(
                "/services/" + str(payload['id']),
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'this is invalid': 'so I should never see this'}}),
                content_type='application/json')

            assert_equal(json.loads(
                response.get_data())['error'], 'JSON was not a valid format')
            assert_equal(response.status_code, 400)

    def test_invalid_field_not_accepted_on_update_for_paas(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-PaaS")

            response = self.client.put(
                '/services/' + str(payload['id']),
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 201)

            response = self.client.post(
                "/services/" + str(payload['id']),
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'this is invalid': 'so I should never see this'}}),
                content_type='application/json')

            assert_equal(json.loads(
                response.get_data())['error'], 'JSON was not a valid format')
            assert_equal(response.status_code, 400)

    def test_invalid_field_not_accepted_on_update_for_scs(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-SCS")

            response = self.client.put(
                '/services/' + str(payload['id']),
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 201)

            response = self.client.post(
                "/services/" + str(payload['id']),
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'this is invalid': 'so I should never see this'}}),
                content_type='application/json')

            assert_equal(json.loads(
                response.get_data())['error'], 'JSON was not a valid format')
        assert_equal(response.status_code, 400)

    def test_invalid_field_value_not_accepted_on_update_for(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-IaaS")
            response = self.client.put(
                '/services/' + str(payload['id']),
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 201)

            response = self.client.post(
                "/services/" + str(payload['id']),
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'}, 'services': {
                        'priceUnit': 'euros'}}),
                content_type='application/json')

            assert_equal(json.loads(
                response.get_data())['error'], 'JSON was not a valid format')
            assert_equal(response.status_code, 400)

    def test_updated_service_should_be_archived(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-IaaS")
            response = self.client.put(
                '/services/' + str(payload['id']),
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 201)

            response = self.client.post(
                '/services/%s' % str(payload['id']),
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'serviceName': 'new service name'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            archived_state = self.client.get(
                '/services-archive?service-id=' +
                str(payload['id'])).get_data()
            archived_service_json = json.loads(archived_state)['services'][0]

            assert_equal(
                archived_service_json['serviceName'], "My Iaas Service")

    def test_updated_service_should_be_archived_on_each_update(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-IaaS")
            response = self.client.put(
                '/services/' + str(payload['id']),
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 201)

            for i in range(5):
                response = self.client.post(
                    '/services/%s' % str(payload['id']),
                    data=json.dumps(
                        {'update_details': {
                            'updated_by': 'joeblogs',
                            'update_reason': 'whateves'},
                         'services': {
                             'serviceName': 'new service name' + str(i)}}),
                    content_type='application/json')

                assert_equal(response.status_code, 200)

            archived_state = self.client.get(
                '/services-archive?service-id=' +
                str(payload['id'])).get_data()
            assert_equal(len(json.loads(archived_state)['services']), 5)

    def test_should_404_if_no_archived_service_found_by_pk(self):
        response = self.client.get('/services-archive/123')
        assert_equal(response.status_code, 404)

    def test_return_empty_list_if_no_archived_service_by_service_id(self):
        response = self.client.get('/services-archive?service-id=123')
        assert_equal(response.status_code, 404)

    def test_should_404_if_non_int_pk(self):
        response = self.client.get('/services-archive/aaa')
        assert_equal(response.status_code, 404)

    def test_should_400_if_invalid_service_id(self):
        response = self.client.get('/services-archive?service-id=aaa')
        assert_equal(response.status_code, 400)
        response = self.client.get('/services-archive?service-id=123.1')
        assert_equal(response.status_code, 400)
        response = self.client.get('/services-archive?service-id=')
        assert_equal(response.status_code, 400)
        response = self.client.get('/services-archive')
        assert_equal(response.status_code, 400)


class TestPutService(BaseApplicationTest, JSONUpdateTestMixin):
    method = "put"
    endpoint = "/services/2"

    def setup(self):
        super(TestPutService, self).setup()
        now = datetime.now()
        payload = self.load_example_listing("SSP-JSON-IaaS")
        with self.app.app_context():
            db.session.add(
                Supplier(supplier_id=1, name=u"Supplier 1")
            )
            db.session.add(Service(service_id=2,
                                   supplier_id=1,
                                   updated_at=now,
                                   created_at=now,
                                   updated_by="tests",
                                   updated_reason="test data",
                                   data=payload))

    def test_update_a_service(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-IaaS")
            response = self.client.put(
                '/services/2',
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 204)
            now = datetime.now()
            service = Service.query.filter(Service.service_id == 2).first()
            assert_equal(service.data, payload)
            assert_not_equal(service.created_at, service.updated_at)
            assert_almost_equal(now, service.updated_at,
                                delta=timedelta(seconds=2))

    def test_add_a_new_service(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-IaaS")
            payload['id'] = 3
            response = self.client.put(
                '/services/3',
                data=json.dumps({'services': payload}),
                content_type='application/json')
            assert_equal(response.status_code, 201)
            now = datetime.now()
            service = Service.query.filter(Service.service_id == 3).first()
            assert_equal(service.data, payload)
            assert_equal(service.created_at, service.updated_at)
            assert_almost_equal(now, service.created_at,
                                delta=timedelta(seconds=2))

    def test_when_service_payload_has_invalid_id(self):
        response = self.client.put(
            '/services/2',
            data=json.dumps({'services': {'id': 3, 'foo': 'bar'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)

    def test_invalid_service_id(self):
        response = self.client.put(
            '/services/abc123',
            data=json.dumps({'services': {'id': 'abc123', 'foo': 'bar'}}),
            content_type='application/json')

        assert_equal(response.status_code, 404)

    def test_add_a_service_with_unknown_supplier_id(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-IaaS")
            payload['id'] = 3
            payload['supplierId'] = 100
            response = self.client.put(
                '/services/3',
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 400)

    def test_supplier_name_in_service_data_is_shadowed(self):
        with self.app.app_context():
            payload = self.load_example_listing("SSP-JSON-IaaS")
            payload['id'] = 3
            payload['supplierId'] = 1
            payload['supplierName'] = u'New Name'

            response = self.client.put(
                '/services/3',
                data=json.dumps({'services': payload}),
                content_type='application/json')

            assert_equal(response.status_code, 201)

            response = self.client.get('/services/3')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
            assert_equal(data['services']['supplierName'], u'Supplier 1')

    def test_write_service_response_back(self):
        response = self.client.get('/services/2')

        response = self.client.put(
            '/services/2',
            data=response.get_data(),
            content_type='application/json')

        assert_equal(response.status_code, 204)


class TestGetService(BaseApplicationTest):
    def setup(self):
        super(TestGetService, self).setup()
        now = datetime.now()
        with self.app.app_context():
            db.session.add(
                Supplier(supplier_id=1, name=u"Supplier 1")
            )
            db.session.add(Service(service_id=123,
                                   supplier_id=1,
                                   updated_at=now,
                                   created_at=now,
                                   updated_by="tests",
                                   updated_reason="test data",
                                   data={'foo': 'bar'}))

    def test_get_non_existent_service(self):
        response = self.client.get('/services/100')
        assert_equal(404, response.status_code)

    def test_invalid_service_id(self):
        response = self.client.get('/services/abc123')
        assert_equal(404, response.status_code)

    def test_get_service(self):
        response = self.client.get('/services/123')

        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal(123, data['services']['id'])

    def test_get_service_returns_supplier_info(self):
        response = self.client.get('/services/123')

        data = json.loads(response.get_data())
        assert_equal(data['services']['supplierId'], 1)
        assert_equal(data['services']['supplierName'], u'Supplier 1')
