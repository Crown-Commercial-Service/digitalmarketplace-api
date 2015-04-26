from datetime import datetime, timedelta

from flask import json
from nose.tools import assert_equal, assert_in, assert_not_equal, \
    assert_almost_equal

from app.models import Service, Supplier, ContactInformation, Framework
from mock import Mock
from app import db, search_api_client
from ..helpers import BaseApplicationTest, JSONUpdateTestMixin, \
    TEST_SUPPLIERS_COUNT
from sqlalchemy.exc import IntegrityError


def first_by_rel(rel, links):
    for link in links:
        if link['rel'] == rel:
            return link


class TestListServices(BaseApplicationTest):
    def test_list_services_with_no_services(self):
        response = self.client.get('/services')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(data['services'], [])

    def test_list_services_only_returns_published(self):
        self.setup_dummy_services_including_unpublished(1)
        response = self.client.get('/services')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 1)
        assert_equal(data['services'][0]['id'], '0')

    def test_list_services_returns_status(self):
        self.setup_dummy_services_including_unpublished(1)
        response = self.client.get('/services')
        data = json.loads(response.get_data())
        service = data['services'][0]

        assert_equal(service['status'], u'published')

    def test_list_services_returns_framework(self):
        self.setup_dummy_services_including_unpublished(1)
        response = self.client.get('/services')
        data = json.loads(response.get_data())
        service = data['services'][0]

        assert_equal(service['frameworkName'], u'G-Cloud 6')

    def test_list_services_returns_supplier_info(self):
        self.setup_dummy_services_including_unpublished(1)
        response = self.client.get('/services')
        data = json.loads(response.get_data())
        service = data['services'][0]

        assert_equal(service['supplierId'], 0)
        assert_equal(service['supplierName'], u'Supplier 0')

    def test_paginated_list_services_page_one(self):
        self.setup_dummy_services_including_unpublished(7)

        response = self.client.get('/services')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 5)
        next_link = self.first_by_rel('next', data['links'])
        assert_in('page=2', next_link['href'])

    def test_paginated_list_services_page_two(self):
        self.setup_dummy_services_including_unpublished(7)

        response = self.client.get('/services?page=2')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 2)
        prev_link = self.first_by_rel('prev', data['links'])
        assert_in('page=1', prev_link['href'])

    def test_paginated_list_services_page_out_of_range(self):
        self.setup_dummy_services_including_unpublished(10)

        response = self.client.get('/services?page=10')

        assert_equal(response.status_code, 404)

    def test_x_forwarded_proto(self):
        self.setup_dummy_services_including_unpublished(1)

        response = self.client.get('/services',
                                   headers={'X-Forwarded-Proto': 'https'})
        data = json.loads(response.get_data())

        assert data['services'][0]['links'][0]['href'].startswith('https://')

    def test_invalid_page_argument(self):
        response = self.client.get('/services?page=a')

        assert_equal(response.status_code, 400)
        assert_in(b'Invalid page argument', response.get_data())

    def test_invalid_supplier_id_argument(self):
        response = self.client.get('/services?supplier_id=a')

        assert_equal(response.status_code, 400)
        assert_in(b'Invalid supplier_id', response.get_data())

    def test_non_existent_supplier_id_argument(self):
        response = self.client.get('/services?supplier_id=54321')

        assert_equal(response.status_code, 404)

    def test_supplier_id_filter(self):
        self.setup_dummy_services_including_unpublished(15)

        response = self.client.get('/services?supplier_id=1')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(
            list(filter(lambda s: s['supplierId'] == 1, data['services'])),
            data['services']
        )

    def test_supplier_id_with_no_services_filter(self):
        self.setup_dummy_services_including_unpublished(15)

        response = self.client.get(
            '/services?supplier_id=%d' % TEST_SUPPLIERS_COUNT
        )
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(
            list(),
            data['services']
        )

    def test_supplier_id_filter_pagination(self):
        self.setup_dummy_services_including_unpublished(21)

        response = self.client.get('/services?supplier_id=1&page=2')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 2)
        assert_equal(
            list(filter(lambda s: s['supplierId'] == 1, data['services'])),
            data['services']
        )

    def test_supplier_id_filter_pagination_links(self):
        self.setup_dummy_services_including_unpublished(21)

        response = self.client.get('/services?supplier_id=1&page=1')
        data = json.loads(response.get_data())

        next_link = self.first_by_rel('next', data['links'])
        assert_in('page=2', next_link['href'])
        assert_in('supplier_id=1', next_link['href'])

    def test_unknown_supplier_id(self):
        self.setup_dummy_services_including_unpublished(15)
        response = self.client.get('/services?supplier_id=100')

        assert_equal(response.status_code, 404)


class TestPostService(BaseApplicationTest):
    service_id = None

    def setup(self):
        super(TestPostService, self).setup()
        payload = self.load_example_listing("G6-IaaS")
        self.service_id = str(payload['id'])
        with self.app.app_context():
            db.session.add(
                Framework(id=1, expired=False, name=u"G-Cloud 6")
            )
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

        self.client.put(
            '/services/%s' % self.service_id,
            data=json.dumps(
                {'update_details': {
                    'updated_by': 'joeblogs',
                    'update_reason': 'whateves'},
                 'services': payload}),
            content_type='application/json')

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

    def test_post_returns_404_if_no_service_to_update(self):
        response = self.client.post(
            "/services/9999999999",
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
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'services': {
                        'serviceName': 'new service name'}}),
                content_type='application/json')

            data = json.loads(response.get_data())
            assert_equal(data['error'],
                         "Invalid JSON must have '['update_details', "
                         "'services']' key(s)")
            assert_equal(response.status_code, 400)

    def test_no_content_type_causes_failure(self):
        with self.app.app_context():
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'serviceName': 'new service name'}}))

            assert_equal(response.status_code, 400)
            assert_in(b'Unexpected Content-Type', response.get_data())

    def test_invalid_content_type_causes_failure(self):
        with self.app.app_context():
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'serviceName': 'new service name'}}),
                content_type='application/octet-stream')

            assert_equal(response.status_code, 400)
            assert_in(b'Unexpected Content-Type', response.get_data())

    def test_invalid_json_causes_failure(self):
        with self.app.app_context():
            response = self.client.post(
                '/services/%s' % self.service_id,
                data="ouiehdfiouerhfuehr",
                content_type='application/json')

            assert_equal(response.status_code, 400)
            assert_in(b'a request that this server could not understand',
                      response.get_data())

    def test_can_post_a_valid_service_update(self):
        with self.app.app_context():
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'serviceName': 'new service name'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.get('/services/%s' % self.service_id)

            data = json.loads(response.get_data())
            assert_equal(data['services']['serviceName'], 'new service name')
            assert_equal(response.status_code, 200)

    def test_can_post_a_valid_service_update_on_several_fields(self):
        with self.app.app_context():
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'serviceName': 'new service name',
                         'incidentEscalation': False,
                         'serviceTypes': ['Compute']}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.get('/services/%s' % self.service_id)

            data = json.loads(response.get_data())
            assert_equal(data['services']['serviceName'], 'new service name')
            assert_equal(data['services']['incidentEscalation'], False)
            assert_equal(data['services']['serviceTypes'][0], 'Compute')
            assert_equal(response.status_code, 200)

    def test_can_post_a_valid_service_update_with_list(self):
        with self.app.app_context():
            support_types = ['Service desk', 'Email',
                             'Phone', 'Live chat', 'Onsite']
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'supportTypes': support_types}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.get('/services/%s' % self.service_id)
            data = json.loads(response.get_data())

            assert_equal(all(i in support_types for i in
                             data['services']['supportTypes']), True)
            assert_equal(response.status_code, 200)

    def test_can_post_a_valid_service_update_with_object(self):
        with self.app.app_context():
            identity_authentication_controls = {
                "value": [
                    "Authentication federation"
                ],
                "assurance": "CESG-assured components"
            }

            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'identityAuthenticationControls':
                             identity_authentication_controls}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.get('/services/%s' % self.service_id)
            data = json.loads(response.get_data())

            updated_auth_controls = \
                data['services']['identityAuthenticationControls']
            assert_equal(response.status_code, 200)
            assert_equal(updated_auth_controls['assurance'],
                         'CESG-assured components')
            assert_equal(len(updated_auth_controls['value']), 1)
            assert_equal('Authentication federation' in
                         updated_auth_controls['value'], True)

    def test_invalid_field_not_accepted_on_update(self):
        with self.app.app_context():
            response = self.client.post(
                "/services/" + self.service_id,
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'thisIsInvalid': 'so I should never see this'}}),
                content_type='application/json')

            assert_equal(response.status_code, 400)
            assert_in('JSON was not a valid format',
                      json.loads(response.get_data())['error'])

    def test_invalid_field_value_not_accepted_on_update(self):
        with self.app.app_context():
            response = self.client.post(
                "/services/" + self.service_id,
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'}, 'services': {
                        'priceUnit': 'per Truth'}}),
                content_type='application/json')

            assert_equal(response.status_code, 400)
            assert_in('JSON was not a valid format',
                      json.loads(response.get_data())['error'])

    def test_updated_service_should_be_archived(self):
        with self.app.app_context():
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'update_details': {
                        'updated_by': 'joeblogs',
                        'update_reason': 'whateves'},
                     'services': {
                         'serviceName': 'new service name'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            archived_state = self.client.get(
                '/archived-services?service-id=' +
                self.service_id).get_data()
            archived_service_json = json.loads(archived_state)['services'][0]

            assert_equal(
                archived_service_json['serviceName'], "My Iaas Service")

    def test_updated_service_should_be_archived_on_each_update(self):
        with self.app.app_context():
            for i in range(5):
                response = self.client.post(
                    '/services/%s' % self.service_id,
                    data=json.dumps(
                        {'update_details': {
                            'updated_by': 'joeblogs',
                            'update_reason': 'whateves'},
                         'services': {
                             'serviceName': 'new service name' + str(i)}}),
                    content_type='application/json')

                assert_equal(response.status_code, 200)

            archived_state = self.client.get(
                '/archived-services?service-id=' +
                self.service_id).get_data()
            assert_equal(len(json.loads(archived_state)['services']), 5)

    def test_writing_full_service_back(self):
        with self.app.app_context():
            response = self.client.get('/services/%s' % self.service_id)
            data = json.loads(response.get_data())

            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {
                        'update_details': {
                            'updated_by': 'joeblogs',
                            'update_reason': 'whateves'},
                        'services': data['services']
                    }
                ),
                content_type='application/json')

            assert_equal(response.status_code, 200)

    def test_should_404_if_no_archived_service_found_by_pk(self):
        response = self.client.get('/archived-services/5')
        assert_equal(response.status_code, 404)

    def test_return_404_if_no_archived_service_by_service_id(self):
        response = self.client.get(
            '/archived-services?service-id=12345678901234')
        assert_equal(response.status_code, 404)

    def test_should_400_if_invalid_service_id(self):
        response = self.client.get('/archived-services?service-id=not-valid')
        assert_equal(response.status_code, 400)
        assert_in(b'Invalid service ID supplied', response.get_data())
        response = self.client.get(
            '/archived-services?service-id=1234567890.1')
        assert_equal(response.status_code, 400)
        assert_in(b'Invalid service ID supplied', response.get_data())
        response = self.client.get('/archived-services?service-id=')
        assert_equal(response.status_code, 400)
        assert_in(b'Invalid service ID supplied', response.get_data())
        response = self.client.get('/archived-services')
        assert_equal(response.status_code, 400)
        assert_in(b'Invalid service ID supplied', response.get_data())

    def test_should_400_if_mismatched_service_id(self):
        response = self.client.post(
            '/services/%s' % self.service_id,
            data=json.dumps(
                {'update_details': {
                    'updated_by': 'joeblogs',
                    'update_reason': 'whateves'},
                 'services': {
                     'serviceName': 'new service name', 'id': 'differentId'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in(b'id parameter must match id in data',
                  response.get_data())


class TestShouldCallSearchApiOnPutToCreateService(BaseApplicationTest):
    def setup(self):
        super(TestShouldCallSearchApiOnPutToCreateService, self).setup()
        with self.app.app_context():
            db.session.add(
                Framework(id=1, expired=False, name="G-Cloud 6")
            )
            db.session.add(
                Supplier(supplier_id=1, name=u"Supplier 1")
            )

            db.session.commit()

    def test_should_index_on_service_put(self):
        with self.app.app_context():
            search_api_client.index = Mock(return_value=True)

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            self.client.put(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'update_details': {
                            'updated_by': 'joeblogs',
                            'update_reason': 'whateves'},
                        'services': payload}
                ),
                content_type='application/json')

            service = Service.query.filter(Service.service_id ==
                                           "1234567890123456").first()
            search_api_client.index.assert_called_with(
                "1234567890123456",
                service.data,
                "Supplier 1"
            )


class TestShouldCallSearchApiOnPutToReplaceService(BaseApplicationTest):
    def setup(self):
        super(TestShouldCallSearchApiOnPutToReplaceService, self).setup()
        now = datetime.now()
        payload = self.load_example_listing("G6-IaaS")
        with self.app.app_context():
            db.session.add(
                Framework(id=1, expired=False, name="G-Cloud 6")
            )
            db.session.add(
                Supplier(supplier_id=1, name=u"Supplier 1")
            )
            db.session.add(Service(service_id="1234567890123456",
                                   supplier_id=1,
                                   updated_at=now,
                                   status='published',
                                   created_at=now,
                                   updated_by="tests",
                                   framework_id=1,
                                   updated_reason="test data",
                                   data=payload))
            db.session.commit()

    def test_should_index_on_service_put(self):
        with self.app.app_context():
            search_api_client.index = Mock(return_value=True)

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            self.client.put(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'update_details': {
                            'updated_by': 'joeblogs',
                            'update_reason': 'whateves'},
                        'services': payload}
                ),
                content_type='application/json')

            service = Service.query.filter(Service.service_id ==
                                           "1234567890123456").first()
            search_api_client.index.assert_called_with(
                "1234567890123456",
                service.data,
                "Supplier 1"
            )

    def test_should_not_index_on_service_put_if_db_exception(self):
        with self.app.app_context():
            search_api_client.index = Mock(return_value=True)
            c = db.session.commit
            db.session.commit = Mock(
                side_effect=IntegrityError(
                    'message', 'statement', 'params', 'orig'))

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            payload['supplierId'] = "1234567890123456"
            self.client.put(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'update_details': {
                            'updated_by': 'joeblogs',
                            'update_reason': 'whateves'},
                        'services': payload}
                ),
                content_type='application/json')

            assert_equal(search_api_client.index.called, False)
            db.session.commit = Mock(side_effect=c)


class TestShouldCallSearchApiOnPost(BaseApplicationTest):
    def setup(self):
        super(TestShouldCallSearchApiOnPost, self).setup()
        now = datetime.now()
        payload = self.load_example_listing("G6-IaaS")
        with self.app.app_context():
            db.session.add(
                Framework(id=1, expired=False, name="G-Cloud 6")
            )
            db.session.add(
                Supplier(supplier_id=1, name=u"Supplier 1")
            )
            db.session.add(Service(service_id="1234567890123456",
                                   supplier_id=1,
                                   updated_at=now,
                                   status='published',
                                   created_at=now,
                                   updated_by="tests",
                                   framework_id=1,
                                   updated_reason="test data",
                                   data=payload))
            db.session.commit()

    def test_should_index_on_service_post(self):
        with self.app.app_context():
            search_api_client.index = Mock(return_value=True)

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            self.client.post(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'update_details': {
                            'updated_by': 'joeblogs',
                            'update_reason': 'whateves'},
                        'services': payload}
                ),
                content_type='application/json')

            service = Service.query.filter(Service.service_id ==
                                           "1234567890123456").first()
            search_api_client.index.assert_called_with(
                "1234567890123456",
                service.data,
                "Supplier 1"
            )

    def test_should_not_index_on_service_post_if_db_exception(self):
        with self.app.app_context():
            search_api_client.index = Mock(return_value=True)
            c = db.session.commit
            db.session.commit = Mock(
                side_effect=IntegrityError(
                    'message', 'statement', 'params', 'orig'))

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            self.client.post(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'update_details': {
                            'updated_by': 'joeblogs',
                            'update_reason': 'whateves'},
                        'services': payload}
                ),
                content_type='application/json')
            assert_equal(search_api_client.index.called, False)
            db.session.commit = Mock(side_effect=c)


class TestPutService(BaseApplicationTest, JSONUpdateTestMixin):
    method = "put"
    endpoint = "/services/1234567890123456"

    def setup(self):
        super(TestPutService, self).setup()
        now = datetime.now()
        payload = self.load_example_listing("G6-IaaS")
        with self.app.app_context():
            db.session.add(
                Framework(id=1, expired=False, name="G-Cloud 6")
            )
            db.session.add(
                Framework(id=2, expired=False, name="G-Cloud 4")
            )
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
            db.session.add(Service(service_id="1234567890123456",
                                   supplier_id=1,
                                   updated_at=now,
                                   status='published',
                                   created_at=now,
                                   updated_by="tests",
                                   framework_id=1,
                                   updated_reason="test data",
                                   data=payload))
            db.session.commit()

    def test_add_a_new_service(self):
        with self.app.app_context():
            search_api_client.index = Mock(return_value="bar")

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            response = self.client.put(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'update_details': {
                            'updated_by': 'joeblogs',
                            'update_reason': 'whateves'},
                        'services': payload}
                ),
                content_type='application/json')

            assert_equal(response.status_code, 201)
            now = datetime.now()
            payload.pop('id', None)
            service = Service.query.filter(Service.service_id ==
                                           "1234567890123456").first()
            assert_equal(service.data, payload)
            assert_equal(service.created_at, service.updated_at)
            assert_almost_equal(now, service.created_at,
                                delta=timedelta(seconds=2))

    def test_add_a_new_service_with_status_disabled(self):
        with self.app.app_context():
            payload = self.load_example_listing("G4")
            payload['id'] = "4-disabled"
            payload['status'] = "disabled"
            response = self.client.put(
                '/services/4-disabled',
                data=json.dumps(
                    {
                        'update_details': {
                            'updated_by': 'joeblogs',
                            'update_reason': 'whateves'},
                        'services': payload}
                ),
                content_type='application/json')

            payload.pop('status', None)
            assert_equal(response.status_code, 201)
            now = datetime.now()
            payload.pop('id', None)
            service = Service.query.filter(Service.service_id ==
                                           "4-disabled").first()
            assert_equal(service.status, 'disabled')
            assert_equal(service.data, payload)
            assert_equal(service.created_at, service.updated_at)
            assert_almost_equal(now, service.created_at,
                                delta=timedelta(seconds=2))

    def test_update_a_service(self):
        with self.app.app_context():
            payload = self.load_example_listing("G6-IaaS")
            response = self.client.post(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'update_details': {
                            'updated_by': 'joeblogs',
                            'update_reason': 'whateves'},
                        'services': payload}
                ),
                content_type='application/json')
            assert_equal(response.status_code, 200)
            assert_equal(json.loads(response.get_data()), {"message": "done"})
            now = datetime.now()
            payload.pop('id', None)
            service = Service.query.filter(Service.service_id ==
                                           "1234567890123456").first()
            assert_equal(service.data, payload)
            assert_not_equal(service.created_at, service.updated_at)
            assert_almost_equal(now, service.updated_at,
                                delta=timedelta(seconds=2))

    def test_when_service_payload_has_mismatched_id(self):
        response = self.client.put(
            '/services/1234567890123456',
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs',
                    'update_reason': 'whateves'},
                'services': {'id': "1234567890123457", 'foo': 'bar'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in(b'id parameter must match id in data',
                  response.get_data())

    def test_when_no_update_details(self):
        response = self.client.put(
            '/services/1234567890123456',
            data=json.dumps({'services': {'id': "1234567890123456",
                                          'foo': 'bar'}}),
            content_type='application/json')

        assert_equal(json.loads(response.get_data())['error'],
                     "Invalid JSON must have '['services', "
                     "'update_details']' key(s)")
        assert_equal(response.status_code, 400)
        assert_in(b'Invalid JSON', response.get_data())

    def test_invalid_service_id_too_short(self):
        response = self.client.put(
            '/services/abc123456',
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs',
                    'update_reason': 'whateves'},
                'services': {'id': 'abc123456', 'foo': 'bar'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in(b'Invalid service ID supplied', response.get_data())

    def test_invalid_service_id_too_long(self):
        response = self.client.put(
            '/services/abcdefghij12345678901',
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs',
                    'update_reason': 'whateves'},
                'services': {'id': 'abcdefghij12345678901', 'foo': 'bar'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in(b'Invalid service ID supplied', response.get_data())

    def test_add_a_service_with_unknown_supplier_id(self):
        with self.app.app_context():
            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "6543210987654321"
            payload['supplierId'] = 100
            response = self.client.put(
                '/services/6543210987654321',
                data=json.dumps(
                    {
                        'update_details': {
                            'updated_by': 'joeblogs',
                            'update_reason': 'whateves'},
                        'services': payload}
                ),
                content_type='application/json')

            assert_equal(response.status_code, 400)
            assert_in(b'Key (supplier_id)=(100) is not present',
                      response.get_data())

    def test_supplier_name_in_service_data_is_shadowed(self):
        with self.app.app_context():
            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            payload['supplierId'] = 1
            payload['supplierName'] = u'New Name'

            response = self.client.put(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'update_details': {
                            'updated_by': 'joeblogs',
                            'update_reason': 'whateves'},
                        'services': payload}
                ),
                content_type='application/json')

            assert_equal(response.status_code, 201)

            response = self.client.get('/services/1234567890123456')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
            assert_equal(data['services']['supplierName'], u'Supplier 1')


class TestGetService(BaseApplicationTest):
    def setup(self):
        super(TestGetService, self).setup()
        now = datetime.now()
        with self.app.app_context():
            db.session.add(
                Framework(id=1, expired=False, name="G-Cloud 6")
            )
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
            db.session.add(Service(service_id="123-published-456",
                                   supplier_id=1,
                                   updated_at=now,
                                   created_at=now,
                                   status='published',
                                   updated_by="tests",
                                   updated_reason="test data",
                                   data={'foo': 'bar'},
                                   framework_id=1))
            db.session.add(Service(service_id="123-disabled-456",
                                   supplier_id=1,
                                   updated_at=now,
                                   created_at=now,
                                   status='disabled',
                                   updated_by="tests",
                                   updated_reason="test data",
                                   data={'foo': 'bar'},
                                   framework_id=1))
            db.session.add(Service(service_id="123-enabled-456",
                                   supplier_id=1,
                                   updated_at=now,
                                   created_at=now,
                                   status='enabled',
                                   updated_by="tests",
                                   updated_reason="test data",
                                   data={'foo': 'bar'},
                                   framework_id=1))
            db.session.commit()

    def test_get_non_existent_service(self):
        response = self.client.get('/services/9999999999')
        assert_equal(404, response.status_code)

    def test_invalid_service_id(self):
        response = self.client.get('/services/abc123')
        assert_equal(400, response.status_code)
        assert_in(b'Invalid service ID supplied', response.get_data())

    def test_get_published_service(self):
        response = self.client.get('/services/123-published-456')
        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal("123-published-456", data['services']['id'])

    def test_get_disabled_service(self):
        response = self.client.get('/services/123-disabled-456')
        assert_equal(404, response.status_code)

    def test_get_enabled_service(self):
        response = self.client.get('/services/123-enabled-456')
        assert_equal(404, response.status_code)

    def test_get_service_returns_supplier_info(self):
        response = self.client.get('/services/123-published-456')
        data = json.loads(response.get_data())
        assert_equal(data['services']['supplierId'], 1)
        assert_equal(data['services']['supplierName'], u'Supplier 1')
