from flask import json
from nose.tools import (assert_equal,
                        assert_in,
                        assert_not_in)

from app.models import (Service,
                        Supplier,
                        Address)
from app import db
from tests.app.helpers import BaseApplicationTest


class TestPostService(BaseApplicationTest):
    endpoint = '/services/{self.service_id}'
    method = 'post'
    service_id = None

    def setup(self):
        super(TestPostService, self).setup()

        payload = self.load_example_listing("G6-IaaS")
        self.service_id = str(payload['id'])
        with self.app.app_context():
            db.session.add(
                Supplier(code=1, name="Supplier 1",
                         addresses=[Address(address_line="{} Dummy Street 1",
                                            suburb="Dummy",
                                            state="ZZZ",
                                            postal_code="0000",
                                            country='Australia')])
            )
            db.session.commit()

        self.client.put(
            '/services/%s' % self.service_id,
            data=json.dumps(
                {'updated_by': 'joeblogs',
                 'services': payload}),
            content_type='application/json')

    def test_can_not_post_to_root_services_url(self):
        response = self.client.post(
            "/services",
            data=json.dumps(
                {'updated_by': 'joeblogs',
                 'services': {
                     'serviceName': 'new service name'}}),
            content_type='application/json')

        assert_equal(response.status_code, 405)

    def test_post_returns_404_if_no_service_to_update(self):
        response = self.client.post(
            "/services/9999999999",
            data=json.dumps(
                {'updated_by': 'joeblogs',
                 'services': {
                     'serviceName': 'new service name'}}),
            content_type='application/json')

        assert_equal(response.status_code, 404)

    def test_no_content_type_causes_failure(self):
        with self.app.app_context():
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'updated_by': 'joeblogs',
                     'services': {
                         'serviceName': 'new service name'}}))

            assert_equal(response.status_code, 400)
            assert_in(b'Unexpected Content-Type', response.get_data())

    def test_invalid_content_type_causes_failure(self):
        with self.app.app_context():
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'updated_by': 'joeblogs',
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
            assert_in(b'Invalid JSON', response.get_data())

    def test_can_post_a_valid_service_update(self):
        with self.app.app_context():
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'updated_by': 'joeblogs',
                     'services': {
                         'serviceName': 'new service name'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            response = self.client.get('/services/%s' % self.service_id)

            data = json.loads(response.get_data())
            assert_equal(data['services']['serviceName'], 'new service name')
            assert_equal(response.status_code, 200)

    def test_valid_service_update_creates_audit_event(self):
        with self.app.app_context():
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'updated_by': 'joeblogs',
                     'services': {
                         'serviceName': 'new service name'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            audit_response = self.client.get('/audit-events')
            assert_equal(audit_response.status_code, 200)
            data = json.loads(audit_response.get_data())

            assert_equal(len(data['auditEvents']), 2)
            assert_equal(data['auditEvents'][0]['type'], 'import_service')

            update_event = data['auditEvents'][1]
            assert_equal(update_event['type'], 'update_service')
            assert_equal(update_event['user'], 'joeblogs')
            assert_equal(update_event['data']['serviceId'], self.service_id)

    def test_service_update_audit_event_links_to_both_archived_services(self):
        with self.app.app_context():
            self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'updated_by': 'joeblogs',
                     'services': {'serviceName': 'new service name'}}),
                content_type='application/json')

            self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'updated_by': 'joeblogs',
                     'services': {'serviceName': 'new new service name'}}),
                content_type='application/json')

            audit_response = self.client.get('/audit-events')

            assert_equal(audit_response.status_code, 200)
            data = json.loads(audit_response.get_data())

            assert_equal(len(data['auditEvents']), 3)
            update_event = data['auditEvents'][1]

            old_version = update_event['links']['oldArchivedService']
            new_version = update_event['links']['newArchivedService']

            assert_in('/archived-services/', old_version)
            assert_in('/archived-services/', new_version)
            assert_equal(
                int(old_version.split('/')[-1]) + 1,
                int(new_version.split('/')[-1])
            )
            assert_equal(
                data['auditEvents'][0]['data']['supplierName'],
                'Supplier 1'
            )
            assert_equal(
                data['auditEvents'][0]['data']['supplierCode'],
                1
            )

    def test_can_post_a_valid_service_update_on_several_fields(self):
        with self.app.app_context():
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'updated_by': 'joeblogs',
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
                    {'updated_by': 'joeblogs',
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
                    {'updated_by': 'joeblogs',
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
                    {'updated_by': 'joeblogs',
                     'services': {
                         'thisIsInvalid': 'so I should never see this'}}),
                content_type='application/json')

            assert_equal(response.status_code, 400)
            assert_in('Additional properties are not allowed',
                      "{}".format(
                          json.loads(response.get_data())['error']['_form']))

    def test_invalid_field_value_not_accepted_on_update(self):

        with self.app.app_context():
            response = self.client.post(
                "/services/" + self.service_id,
                data=json.dumps(
                    {'updated_by': 'joeblogs',
                     'services': {
                         'priceUnit': 'per Truth'}}),
                content_type='application/json')

            assert_equal(response.status_code, 400)
            assert_in("no_unit_specified",
                      json.loads(response.get_data())['error']['priceUnit'])

    def test_updated_service_is_archived_right_away(self):
        with self.app.app_context():
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'updated_by': 'joeblogs',
                     'services': {
                         'serviceName': 'new service name'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            archived_state = self.client.get(
                '/archived-services?service-id=' +
                self.service_id).get_data()
            archived_service_json = json.loads(archived_state)['services'][-1]

            assert_equal(archived_service_json['serviceName'],
                         'new service name')

    def test_updated_service_archive_is_listed_in_chronological_order(self):
        with self.app.app_context():
            response = self.client.post(
                '/services/%s' % self.service_id,
                data=json.dumps(
                    {'updated_by': 'joeblogs',
                     'services': {
                         'serviceName': 'new service name'}}),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            archived_state = self.client.get(
                '/archived-services?service-id=' +
                self.service_id).get_data()
            archived_service_json = json.loads(archived_state)['services']

            assert_equal(
                [s['serviceName'] for s in archived_service_json],
                ['My Iaas Service', 'new service name'])

    def test_updated_service_should_be_archived_on_each_update(self):

        with self.app.app_context():
            for i in range(5):
                response = self.client.post(
                    '/services/%s' % self.service_id,
                    data=json.dumps(
                        {'updated_by': 'joeblogs',
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
                        'updated_by': 'joeblogs',
                        'services': data['services']
                    }
                ),
                content_type='application/json')

            assert_equal(response.status_code, 200, response.get_data())

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
                {'updated_by': 'joeblogs',
                 'services': {
                     'serviceName': 'new service name', 'id': 'differentId'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in(b'id parameter must match id in data',
                  response.get_data())

    def test_should_not_update_status_through_service_post(self):
        response = self.client.post(
            '/services/%s' % self.service_id,
            data=json.dumps(
                {'updated_by': 'joeblogs',
                 'services': {
                     'status': 'enabled'}}),
            content_type='application/json')

        assert_equal(response.status_code, 200)

        response = self.client.get('/services/%s' % self.service_id)
        data = json.loads(response.get_data())

        assert_equal(data['services']['status'], 'published')

    def test_should_update_service_with_valid_statuses(self):
        # Statuses are defined in the Supplier model
        valid_statuses = [
            "published",
            "enabled",
            "disabled"
        ]

        for status in valid_statuses:
            response = self.client.post(
                '/services/{0}/status/{1}'.format(
                    self.service_id,
                    status
                ),
                data=json.dumps(
                    {'updated_by': 'joeblogs'}),
                content_type='application/json'
            )

            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())
            assert_equal(status, data['services']['status'])

    def test_update_service_status_creates_audit_event(self):
        response = self.client.post(
            '/services/{0}/status/{1}'.format(
                self.service_id,
                "disabled"
            ),
            data=json.dumps(
                {'updated_by': 'joeblogs'}),
            content_type='application/json'
        )

        assert_equal(response.status_code, 200)

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())

        assert_equal(len(data['auditEvents']), 2)
        assert_equal(data['auditEvents'][0]['type'], 'import_service')
        assert_equal(data['auditEvents'][1]['type'], 'update_service_status')
        assert_equal(data['auditEvents'][1]['user'], 'joeblogs')
        assert_equal(
            data['auditEvents'][1]['data']['serviceId'], self.service_id
        )
        assert_equal(data['auditEvents'][1]['data']['new_status'], 'disabled')
        assert_equal(data['auditEvents'][1]['data']['old_status'], 'published')
        assert_in('/archived-services/',
                  data['auditEvents'][1]['links']['oldArchivedService'])
        assert_in('/archived-services/',
                  data['auditEvents'][1]['links']['newArchivedService'])

    def test_should_400_with_invalid_statuses(self):
        invalid_statuses = [
            "unpublished",  # not a permissible state
            "enabeld",  # typo
        ]

        valid_statuses = [
            "published",
            "enabled",
            "disabled"
        ]

        for status in invalid_statuses:
            response = self.client.post(
                '/services/{0}/status/{1}'.format(
                    self.service_id,
                    status
                ),
                data=json.dumps(
                    {'updated_by': 'joeblogs'}),
                content_type='application/json'
            )

            assert_equal(response.status_code, 400)
            assert_in('is not a valid status',
                      json.loads(response.get_data())['error'])
            # assert that valid status names are returned in the response
            for valid_status in valid_statuses:
                assert_in(valid_status,
                          json.loads(response.get_data())['error'])

    def test_should_404_without_status_parameter(self):
        response = self.client.post(
            '/services/{0}/status/'.format(
                self.service_id,
            ),
            data=json.dumps(
                {'updated_by': 'joeblogs'}),
            content_type='application/json'
        )

        assert_equal(response.status_code, 404)

    def test_json_postgres_field_should_not_include_column_fields(self):

        non_json_fields = [
            'supplierName', 'links', 'frameworkSlug', 'updatedAt', 'createdAt', 'frameworkName', 'status', 'id']
        with self.app.app_context():
            response = self.client.get('/services/{}'.format(self.service_id))
            data = json.loads(response.get_data())

            response = self.client.post(
                '/services/{}'.format(self.service_id),
                data=json.dumps({
                    'updated_by': 'joeblogs',
                    'services': data['services'],
                }),
                content_type='application/json')

            assert_equal(response.status_code, 200)

            service = Service.query.filter(
                Service.service_id == self.service_id
            ).first()

            for key in non_json_fields:
                assert_not_in(key, service.data)

    def test_update_g5_service(self):
        with self.app.app_context():
            payload = self.load_example_listing('G5')

            response = self.client.put('/services/{}'.format(payload['id']),
                                       data=json.dumps({
                                           'services': payload,
                                           "updated_by": "joeblogs",
                                       }),
                                       content_type='application/json')

            assert_equal(response.status_code, 201)

            response = self.client.post('/services/{}'.format(payload['id']),
                                        data=json.dumps({
                                            "services": {
                                                "serviceName": "fooo",
                                            },
                                            "updated_by": "joeblogs"
                                        }),
                                        content_type='application/json')
            assert_equal(response.status_code, 200)
