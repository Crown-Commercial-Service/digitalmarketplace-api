import os
from datetime import datetime, timedelta

import mock
from dmapiclient import HTTPError
from dmapiclient.audit import AuditTypes
from dmutils.formats import DATETIME_FORMAT
from flask import json
from nose.tools import assert_equal, assert_in, assert_true, \
    assert_almost_equal, assert_false, assert_is_not_none, assert_not_in
from sqlalchemy.exc import IntegrityError

from app import db, create_app
from app.models import Service, Supplier, ContactInformation, Framework, \
    AuditEvent, FrameworkLot
from ..helpers import BaseApplicationTest, JSONUpdateTestMixin, \
    TEST_SUPPLIERS_COUNT


class TestListServicesOrdering(BaseApplicationTest):

    def setup_services(self):
        with self.app.app_context():
            now = datetime.utcnow()

            g5_saas = self.load_example_listing("G5")
            g5_paas = self.load_example_listing("G5")
            g6_paas_2 = self.load_example_listing("G6-PaaS")
            g6_iaas_1 = self.load_example_listing("G6-IaaS")
            g6_paas_1 = self.load_example_listing("G6-PaaS")
            g6_saas = self.load_example_listing("G6-SaaS")
            g6_iaas_2 = self.load_example_listing("G6-IaaS")

            db.session.add(
                Supplier(supplier_id=1, name=u"Supplier 1")
            )

            def insert_service(listing, service_id, lot_id, framework_id):
                db.session.add(Service(service_id=service_id,
                                       supplier_id=1,
                                       updated_at=now,
                                       status='published',
                                       created_at=now,
                                       lot_id=lot_id,
                                       framework_id=framework_id,
                                       data=listing))

            # override certain fields to create ordering difference
            g6_iaas_1['serviceName'] = "b service name"
            g6_iaas_2['serviceName'] = "a service name"
            g6_paas_1['serviceName'] = "b service name"
            g6_paas_2['serviceName'] = "a service name"
            g5_paas['lot'] = "PaaS"

            insert_service(g5_paas, "123-g5-paas", 2, 3)
            insert_service(g5_saas, "123-g5-saas", 1, 3)
            insert_service(g6_iaas_1, "123-g6-iaas-1", 3, 1)
            insert_service(g6_iaas_2, "123-g6-iaas-2", 3, 1)
            insert_service(g6_paas_1, "123-g6-paas-1", 2, 1)
            insert_service(g6_paas_2, "123-g6-paas-2", 2, 1)
            insert_service(g6_saas, "123-g6-saas", 1, 1)

            db.session.commit()

    def test_should_order_supplier_services_by_framework_lot_name(self):
        self.setup_services()

        response = self.client.get('/services?supplier_id=1')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal([d['id'] for d in data['services']], [
            '123-g6-saas',
            '123-g6-paas-2',
            '123-g6-paas-1',
            '123-g6-iaas-2',
            '123-g6-iaas-1',
            '123-g5-saas',
            '123-g5-paas',
        ])

    def test_all_services_list_ordered_by_id(self):
        self.setup_services()

        p1 = self.client.get('/services')
        p2 = self.client.get('/services?page=2')

        services = json.loads(p1.get_data())['services'] + json.loads(p2.get_data())['services']

        assert_equal(p1.status_code, 200)
        assert_equal(p2.status_code, 200)

        print [d['id'] for d in services]
        assert_equal([d['id'] for d in services], [
            '123-g5-paas',
            '123-g5-saas',
            '123-g6-iaas-1',
            '123-g6-iaas-2',
            '123-g6-paas-1',
            '123-g6-paas-2',
            '123-g6-saas',
        ])


class TestListServices(BaseApplicationTest):

    def setup_services(self):
        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            self.set_framework_status('digital-outcomes-and-specialists', 'live')
            self.setup_dummy_service(
                service_id='10000000001',
                supplier_id=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=5,  # digital-outcomes
                data={"locations": [
                    "London", "Offsite", "Scotland", "Wales"
                ]
                })
            self.setup_dummy_service(
                service_id='10000000002',
                supplier_id=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=6,  # digital-specialists
                data={"agileCoachLocations": ["London", "Offsite", "Scotland", "Wales"]}
            )
            self.setup_dummy_service(
                service_id='10000000003',
                supplier_id=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=6,  # digital-specialists
                data={"agileCoachLocations": ["Wales"]}
            )
            db.session.commit()

    def test_list_services_with_no_services(self):
        response = self.client.get('/services')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(data['services'], [])

    def test_list_services_gets_all_statuses(self):
        self.setup_dummy_services_including_unpublished(1)
        response = self.client.get('/services')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 3)

    def test_list_services_returns_updated_date(self):
        self.setup_dummy_services_including_unpublished(1)
        response = self.client.get('/services')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        try:
            datetime.strptime(
                data['services'][0]['updatedAt'], DATETIME_FORMAT)
            assert True, "Parsed date"
        except ValueError:
            assert False, "Should be able to parse date"

    def test_list_services_gets_only_active_frameworks(self):
        with self.app.app_context():
            self.setup_dummy_service(
                service_id='2000000999',
                status='published',
                framework_id=2)
            self.setup_dummy_services_including_unpublished(1)

            response = self.client.get('/services')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
            assert_equal(len(data['services']), 3)

    def test_list_services_with_given_frameworks(self):
        with self.app.app_context():
            self.setup_dummy_services_including_unpublished(1)

            self.setup_dummy_service(
                service_id='2000000998',
                status='published',
                framework_id=2)
            self.setup_dummy_service(
                service_id='2000000999',
                status='published',
                framework_id=3)

            response = self.client.get('/services?framework=g-cloud-4')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
            assert_equal(len(data['services']), 1)

            response = self.client.get('/services?framework=g-cloud-4,g-cloud-5')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
            assert_equal(len(data['services']), 2)

    def test_gets_only_active_frameworks_with_status_filter(self):
        with self.app.app_context():
            self.setup_dummy_service(
                service_id='2000000999',
                status='published',
                framework_id=2)
            self.setup_dummy_services_including_unpublished(1)

            response = self.client.get('/services?status=published')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
            assert_equal(len(data['services']), 1)

    def test_list_services_gets_only_published(self):
        self.setup_dummy_services_including_unpublished(1)
        response = self.client.get('/services?status=published')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 1)
        assert_equal(data['services'][0]['id'], '2000000000')

    def test_list_services_gets_only_enabled(self):
        self.setup_dummy_services_including_unpublished(1)
        response = self.client.get('/services?status=enabled')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 1)
        assert_equal(data['services'][0]['id'], '2000000003')

    def test_list_services_gets_only_disabled(self):
        self.setup_dummy_services_including_unpublished(1)
        response = self.client.get('/services?status=disabled')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 1)
        assert_equal(data['services'][0]['id'], '2000000002')

    def test_list_services_gets_combination_of_enabled_and_disabled(self):
        self.setup_dummy_services_including_unpublished(1)
        response = self.client.get('/services?status=disabled,enabled')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 2)
        assert_equal(data['services'][0]['id'], '2000000002')
        assert_equal(data['services'][1]['id'], '2000000003')

    def test_list_services_gets_combination_of_enabled_and_published(self):
        self.setup_dummy_services_including_unpublished(1)
        response = self.client.get('/services?status=published,enabled')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 2)
        assert_equal(data['services'][0]['id'], '2000000000')
        assert_equal(data['services'][1]['id'], '2000000003')

    def test_list_services_returns_framework_and_lot_info(self):
        self.setup_dummy_services_including_unpublished(1)
        response = self.client.get('/services')
        data = json.loads(response.get_data())
        service = data['services'][0]

        framework_info = {
            key: value for key, value in data['services'][0].items()
            if key.startswith('framework') or key.startswith('lot')
        }
        assert framework_info == {
            'frameworkSlug': 'g-cloud-6',
            'frameworkName': 'G-Cloud 6',
            'frameworkStatus': 'live',
            'frameworkFramework': 'g-cloud',
            'lot': 'saas',
            'lotSlug': 'saas',
            'lotName': 'Software as a Service',
        }

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
        assert_in('page=2', data['links']['next'])
        assert_in('page=2', data['links']['last'])

    def test_paginated_list_services_page_two(self):
        self.setup_dummy_services_including_unpublished(7)

        response = self.client.get('/services?page=2')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 4)
        prev_link = data['links']['prev']
        assert_in('page=1', prev_link)

    def test_paginated_list_services_page_out_of_range(self):
        self.setup_dummy_services_including_unpublished(10)

        response = self.client.get('/services?page=10')

        assert_equal(response.status_code, 404)

    def test_below_one_page_number_is_404(self):
        response = self.client.get('/services?page=0')

        assert_equal(response.status_code, 404)

    def test_x_forwarded_proto(self):
        prev_environ = os.environ.get('DM_HTTP_PROTO')
        os.environ['DM_HTTP_PROTO'] = 'https'
        app = create_app('test')

        with app.app_context():
            client = app.test_client()
            self.setup_authorization(app)
            response = client.get('/')
            data = json.loads(response.get_data())

        if prev_environ is None:
            del os.environ['DM_HTTP_PROTO']
        else:
            os.environ['DM_HTTP_PROTO'] = prev_environ

        assert data['links']['services.list'].startswith('https://')

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

    def test_supplier_should_get_all_service_on_one_page(self):
        self.setup_dummy_services_including_unpublished(21)

        response = self.client.get('/services?supplier_id=1')
        data = json.loads(response.get_data())
        assert_not_in('next', data['links'])
        assert_equal(len(data['services']), 7)

    def test_unknown_supplier_id(self):
        self.setup_dummy_services_including_unpublished(15)
        response = self.client.get('/services?supplier_id=100')

        assert_equal(response.status_code, 404)

    def test_filter_services_by_lot_location_role(self):
        self.setup_services()
        response = self.client.get('/services?lot=digital-specialists')
        data = json.loads(response.get_data())
        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 2)

        response = self.client.get('/services?lot=digital-outcomes')
        data = json.loads(response.get_data())
        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 1)

        response = self.client.get('/services?lot=digital-specialists&location=London&role=agileCoach')
        data = json.loads(response.get_data())
        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 1)

        response = self.client.get('/services?lot=digital-specialists&location=Wales&role=agileCoach')
        data = json.loads(response.get_data())
        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 2)

        response = self.client.get('/services?lot=digital-specialists&role=agileCoach')
        data = json.loads(response.get_data())
        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 2)

    def test_cannot_filter_services_by_location_without_lot(self):
        self.setup_services()
        response = self.client.get('/services?location=Wales')
        data = json.loads(response.get_data())
        assert response.status_code == 400
        assert data['error'] == 'Lot must be specified to filter by location'

    def test_can_only_filter_by_role_for_specialists_lot(self):
        self.setup_services()
        response = self.client.get('/services?lot=digital-outcomes&role=agileCoach')
        data = json.loads(response.get_data())
        assert response.status_code == 400
        assert data['error'] == 'Role only applies to Digital Specialists lot'

    def test_role_required_for_digital_specialists_location_query(self):
        self.setup_services()
        response = self.client.get('/services?lot=digital-specialists&location=Wales')
        data = json.loads(response.get_data())
        assert response.status_code == 400
        assert data['error'] == 'Role must be specified for Digital Specialists'


class TestPostService(BaseApplicationTest, JSONUpdateTestMixin):
    endpoint = '/services/{self.service_id}'
    method = 'post'

    def setup(self):
        payload = self.load_example_listing("G6-IaaS")
        self.service_id = str(payload['id'])
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
                data['auditEvents'][0]['data']['supplierId'],
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
        archived_state = self.client.get(
            '/archived-services?service-id=' +
            self.service_id).get_data()
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
        # There is an update in the setup, there are actually 6
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


@mock.patch('app.service_utils.search_api_client')
class TestShouldCallSearchApiOnPutToCreateService(BaseApplicationTest):
    def setup(self):
        with self.app.app_context():
            db.session.add(
                Supplier(supplier_id=1, name=u"Supplier 1")
            )

            db.session.commit()

    def test_should_index_on_service_put(self, search_api_client):
        with self.app.app_context():
            search_api_client.index.return_value = True

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            response = self.client.put(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': payload}
                ),
                content_type='application/json')

            search_api_client.index.assert_called_with(
                "1234567890123456",
                json.loads(response.get_data())['services']
            )

    def test_should_not_index_on_service_on_expired_frameworks(
            self, search_api_client
    ):
        with self.app.app_context():
            search_api_client.index.return_value = True

            payload = self.load_example_listing("G4")
            res = self.client.put(
                '/services/' + payload["id"],
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': payload}
                ),
                content_type='application/json')

            assert_equal(res.status_code, 201)
            assert_is_not_none(Service.query.filter(
                Service.service_id == payload["id"]).first())
            assert_false(search_api_client.index.called)

    def test_should_ignore_index_error_on_service_put(self, search_api_client):
        with self.app.app_context():
            search_api_client.index.side_effect = HTTPError()

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            response = self.client.put(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': payload}
                ),
                content_type='application/json')

            assert_equal(response.status_code, 201)


@mock.patch('app.service_utils.search_api_client')
class TestShouldCallSearchApiOnPost(BaseApplicationTest):
    def setup(self):
        now = datetime.utcnow()
        payload = self.load_example_listing("G6-IaaS")
        g4_payload = self.load_example_listing("G4")
        with self.app.app_context():
            db.session.add(
                Supplier(supplier_id=1, name=u"Supplier 1")
            )
            db.session.add(Service(service_id="1234567890123456",
                                   supplier_id=1,
                                   updated_at=now,
                                   status='published',
                                   created_at=now,
                                   lot_id=3,
                                   framework_id=1,
                                   data=payload))
            db.session.add(Service(service_id="4-G2-0123-456",
                                   supplier_id=1,
                                   updated_at=now,
                                   status='published',
                                   created_at=now,
                                   lot_id=3,
                                   framework_id=2,  # G-Cloud 4
                                   data=g4_payload))
            db.session.commit()

    def test_should_index_on_service_post(self, search_api_client):
        with self.app.app_context():
            search_api_client.index.return_value = True

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            self.client.post(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': payload}
                ),
                content_type='application/json')

            search_api_client.index.assert_called_with(
                "1234567890123456",
                mock.ANY
            )

    @mock.patch('app.service_utils.db.session.commit')
    def test_should_not_index_on_service_post_if_db_exception(
            self, search_api_client, db_session_commit
    ):
        with self.app.app_context():
            search_api_client.index.return_value = True
            db_session_commit.side_effect = IntegrityError(
                'message', 'statement', 'params', 'orig')

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            self.client.post(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': payload}
                ),
                content_type='application/json')
            assert_equal(search_api_client.index.called, False)

    def test_should_not_index_on_service_on_expired_frameworks(
            self, search_api_client
    ):
        with self.app.app_context():
            search_api_client.index.return_value = True

            payload = self.load_example_listing("G4")
            res = self.client.post(
                '/services/4-G2-0123-456',
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': payload}
                ),
                content_type='application/json')

            assert_equal(res.status_code, 200)
            assert_false(search_api_client.index.called)

    def test_should_ignore_index_error(self, search_api_client):
        with self.app.app_context():
            search_api_client.index.side_effect = HTTPError()

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            response = self.client.post(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': payload}
                ),
                content_type='application/json')

            assert_equal(response.status_code, 200, response.get_data())


class TestShouldCallSearchApiOnPostStatusUpdate(BaseApplicationTest):
    def setup(self):
        now = datetime.utcnow()
        self.services = {}

        valid_statuses = [
            'published',
            'enabled',
            'disabled'
        ]

        with self.app.app_context():
            db.session.add(
                Supplier(supplier_id=1, name=u"Supplier 1")
            )

            for index, status in enumerate(valid_statuses):
                payload = self.load_example_listing("G6-IaaS")

                # give each service a different id.
                new_id = int(payload['id']) + index
                payload['id'] = "{}".format(new_id)

                self.services[status] = payload

                db.session.add(Service(service_id=self.services[status]['id'],
                                       supplier_id=1,
                                       updated_at=now,
                                       status=status,
                                       created_at=now,
                                       lot_id=1,
                                       framework_id=1,
                                       data=self.services[status]))

            db.session.commit()
            assert_equal(3, db.session.query(Service).count())

    def _get_service_from_database_by_service_id(self, service_id):
        with self.app.app_context():
            return Service.query.filter(
                Service.service_id == service_id).first()

    def _post_update_status(self, old_status, new_status,
                            service_is_indexed, service_is_deleted,
                            expected_status_code):

        with mock.patch('app.service_utils.search_api_client') \
                as search_api_client:

            search_api_client.index.return_value = True
            search_api_client.delete.return_value = True

            response = self.client.post(
                '/services/{0}/status/{1}'.format(
                    self.services[old_status]['id'],
                    new_status
                ),
                data=json.dumps(
                    {'updated_by': 'joeblogs'}),
                content_type='application/json'
            )

            # Check response after posting an update
            assert_equal(response.status_code, expected_status_code)

            # Exit function if update was not successful
            if expected_status_code != 200:
                return

            service = self._get_service_from_database_by_service_id(
                self.services[old_status]['id'])

            # Check that service in database has been updated
            assert_equal(new_status, service.status)

            # Check that search_api_client is doing the right thing
            if service_is_indexed:
                search_api_client.index.assert_called_with(
                    service.service_id,
                    json.loads(response.get_data())['services']
                )
            else:
                assert_false(search_api_client.index.called)

            if service_is_deleted:
                search_api_client.delete.assert_called_with(service.service_id)
            else:
                assert_false(search_api_client.delete.called)

    def test_should_index_on_service_status_changed_to_published(self):

        self._post_update_status(
            old_status='enabled',
            new_status='published',
            service_is_indexed=True,
            service_is_deleted=False,
            expected_status_code=200,
        )

    def test_should_not_index_on_service_status_was_already_published(self):

        self._post_update_status(
            old_status='published',
            new_status='published',
            service_is_indexed=False,
            service_is_deleted=False,
            expected_status_code=200,
        )

    def test_should_delete_on_update_service_status_to_not_published(self):

        self._post_update_status(
            old_status='published',
            new_status='enabled',
            service_is_indexed=False,
            service_is_deleted=True,
            expected_status_code=200,
        )

    def test_should_not_delete_on_service_status_was_never_published(self):

        self._post_update_status(
            old_status='disabled',
            new_status='enabled',
            service_is_indexed=False,
            service_is_deleted=False,
            expected_status_code=200,
        )

    @mock.patch('app.search_api_client')
    def test_should_ignore_index_error(self, search_api_client):
        search_api_client.index.side_effect = HTTPError()

        response = self.client.post(
            '/services/{0}/status/{1}'.format(
                self.services['enabled']['id'],
                'published'
            ),
            data=json.dumps(
                {'updated_by': 'joeblogs'}),
            content_type='application/json'
        )

        assert_equal(response.status_code, 200)

    @mock.patch('app.search_api_client')
    def test_should_ignore_index_delete_error(self, search_api_client):
        search_api_client.delete.side_effect = HTTPError()

        response = self.client.post(
            '/services/{0}/status/{1}'.format(
                self.services['published']['id'],
                'enabled'
            ),
            data=json.dumps(
                {'updated_by': 'joeblogs'}),
            content_type='application/json'
        )

        assert_equal(response.status_code, 200)


class TestPutService(BaseApplicationTest, JSONUpdateTestMixin):
    method = "put"
    endpoint = "/services/1234567890123456"

    def setup(self):
        payload = self.load_example_listing("G6-IaaS")
        del payload['id']
        with self.app.app_context():
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

    def test_json_postgres_data_column_should_not_include_column_fields(self):
        non_json_fields = [
            'supplierName', 'links', 'frameworkSlug', 'updatedAt', 'createdAt', 'frameworkName', 'status', 'id',
            'supplierId', 'updatedAt', 'createdAt']
        with self.app.app_context():
            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"

            response = self.client.put(
                '/services/1234567890123456',
                data=json.dumps({
                    'updated_by': 'joeblogs',
                    'services': payload,
                }),
                content_type='application/json')

            assert_equal(response.status_code, 201)

            service = Service.query.filter(
                Service.service_id == "1234567890123456"
            ).first()

            for key in non_json_fields:
                assert_not_in(key, service.data)

    @mock.patch('app.search_api_client')
    def test_add_a_new_service(self, search_api_client):
        with self.app.app_context():
            search_api_client.index.return_value = "bar"

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            response = self.client.put(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': payload}
                ),
                content_type='application/json')

            assert_equal(response.status_code, 201)
            now = datetime.utcnow()

            response = self.client.get("/services/1234567890123456")
            service = json.loads(response.get_data())["services"]

            assert_equal(
                service["id"],
                payload['id'])

            assert_equal(
                service["supplierId"],
                payload['supplierId'])

            assert_equal(
                self.string_to_time_to_string(
                    service["createdAt"],
                    DATETIME_FORMAT,
                    "%Y-%m-%dT%H:%M:%SZ"),
                payload['createdAt'])

            assert_almost_equal(
                self.string_to_time(service["updatedAt"], DATETIME_FORMAT),
                now,
                delta=timedelta(seconds=2))

    @mock.patch('app.search_api_client')
    def test_whitespace_is_stripped_on_import(self, search_api_client):
        with self.app.app_context():
            search_api_client.index.return_value = "bar"

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            payload['serviceSummary'] = "    A new summary with   space    "
            payload['serviceFeatures'] = ["    ",
                                          "    A feature   with space    ",
                                          "",
                                          "    A second feature with space   "]
            response = self.client.put(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': payload}
                ),
                content_type='application/json')

            assert_equal(response.status_code, 201, response.get_data())

            response = self.client.get("/services/1234567890123456")
            service = json.loads(response.get_data())["services"]

            assert_equal(
                service["serviceSummary"],
                "A new summary with   space"
            )
            assert_equal(len(service["serviceFeatures"]), 2)
            assert_equal(
                service["serviceFeatures"][0],
                "A feature   with space"
            )
            assert_equal(
                service["serviceFeatures"][1],
                "A second feature with space"
            )

    @mock.patch('app.search_api_client')
    def test_add_a_new_service_creates_audit_event(self, search_api_client):
        with self.app.app_context():
            search_api_client.index.return_value = "bar"

            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            response = self.client.put(
                '/services/1234567890123456',
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': payload}
                ),
                content_type='application/json')

            assert_equal(response.status_code, 201)

            audit_response = self.client.get('/audit-events')
            assert_equal(audit_response.status_code, 200)
            data = json.loads(audit_response.get_data())

            assert_equal(len(data['auditEvents']), 1)
            assert_equal(data['auditEvents'][0]['type'], 'import_service')
            assert_equal(
                data['auditEvents'][0]['user'],
                'joeblogs')
            assert_equal(data['auditEvents'][0]['data']['serviceId'],
                         "1234567890123456")
            assert_equal(data['auditEvents'][0]['data']['supplierName'],
                         "Supplier 1")
            assert_equal(data['auditEvents'][0]['data']['supplierId'],
                         1)
            assert_equal(
                data['auditEvents'][0]['data']['oldArchivedServiceId'], None
            )
            assert_not_in('old_archived_service',
                          data['auditEvents'][0]['links'])

            assert_true(isinstance(
                data['auditEvents'][0]['data']['newArchivedServiceId'], int
            ))
            assert_in('newArchivedService', data['auditEvents'][0]['links'])

    def test_add_a_new_service_with_status_disabled(self):
        with self.app.app_context():
            payload = self.load_example_listing("G4")
            payload['id'] = "4-disabled"
            payload['status'] = "disabled"
            response = self.client.put(
                '/services/4-disabled',
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': payload}
                ),
                content_type='application/json')

            for field in ['id', 'lot', 'supplierId', 'status']:
                payload.pop(field, None)
            assert_equal(response.status_code, 201, response.get_data())
            now = datetime.utcnow()
            service = Service.query.filter(Service.service_id == "4-disabled").first()
            assert_equal(service.status, 'disabled')
            for key in service.data:
                assert_equal(service.data[key], payload[key])
            assert_almost_equal(service.created_at, service.updated_at,
                                delta=timedelta(seconds=0.5))
            assert_almost_equal(now, service.created_at,
                                delta=timedelta(seconds=2))

    def test_when_service_payload_has_mismatched_id(self):
        response = self.client.put(
            '/services/1234567890123456',
            data=json.dumps({
                'updated_by': 'joeblogs',
                'services': {'id': "1234567890123457", 'foo': 'bar'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in(b'id parameter must match id in data',
                  response.get_data())

    def test_invalid_service_id_too_short(self):
        response = self.client.put(
            '/services/abc123456',
            data=json.dumps({
                'updated_by': 'joeblogs',
                'services': {'id': 'abc123456', 'foo': 'bar'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in(b'Invalid service ID supplied', response.get_data())

    def test_invalid_service_id_too_long(self):
        response = self.client.put(
            '/services/abcdefghij12345678901',
            data=json.dumps({
                'updated_by': 'joeblogs',
                'services': {'id': 'abcdefghij12345678901', 'foo': 'bar'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in(b'Invalid service ID supplied', response.get_data())

    def test_invalid_service_status(self):
        payload = self.load_example_listing("G4")
        payload['id'] = "4-invalid-status"
        payload['status'] = "foo"
        response = self.client.put(
            '/services/4-invalid-status',
            data=json.dumps({
                'updated_by': 'joeblogs',
                'services': payload}),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in("Invalid status value 'foo'", json.loads(response.get_data())['error'])

    def test_invalid_service_lot(self):
        payload = self.load_example_listing("G4")
        payload['id'] = "4-invalid-lot"
        payload['lot'] = "foo"
        response = self.client.put(
            '/services/4-invalid-lot',
            data=json.dumps({
                'updated_by': 'joeblogs',
                'services': payload}),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in("Incorrect lot 'foo' for framework 'g-cloud-4'", json.loads(response.get_data())['error'])

    def test_invalid_service_data(self):
        payload = self.load_example_listing("G6-IaaS")
        payload['id'] = "1234567890123456"

        payload['priceMin'] = 23.45

        response = self.client.put(
            '/services/1234567890123456',
            data=json.dumps({
                'updated_by': 'joeblogs',
                'services': payload
            }),
            content_type='application/json')

        assert_equal(response.status_code, 400)
        assert_in("23.45 is not of type", json.loads(response.get_data())['error']['priceMin'])

    def test_add_a_service_with_unknown_supplier_id(self):
        with self.app.app_context():
            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "6543210987654321"
            payload['supplierId'] = 100
            response = self.client.put(
                '/services/6543210987654321',
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': payload}
                ),
                content_type='application/json')

            assert_equal(response.status_code, 400)
            assert_in("Invalid supplier ID '100'", json.loads(response.get_data())['error'])

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
                        'updated_by': 'joeblogs',
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
        now = datetime.utcnow()
        with self.app.app_context():
            db.session.add(Framework(
                id=123,
                name="expired",
                slug="expired",
                framework="g-cloud",
                status="expired",
            ))
            db.session.commit()
            db.session.add(FrameworkLot(
                framework_id=123,
                lot_id=1
            ))
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
                                   data={'foo': 'bar'},
                                   lot_id=1,
                                   framework_id=1))
            db.session.add(Service(service_id="123-disabled-456",
                                   supplier_id=1,
                                   updated_at=now,
                                   created_at=now,
                                   status='disabled',
                                   data={'foo': 'bar'},
                                   lot_id=1,
                                   framework_id=1))
            db.session.add(Service(service_id="123-enabled-456",
                                   supplier_id=1,
                                   updated_at=now,
                                   created_at=now,
                                   status='enabled',
                                   data={'foo': 'bar'},
                                   lot_id=1,
                                   framework_id=1))
            db.session.add(Service(service_id="123-expired-456",
                                   supplier_id=1,
                                   updated_at=now,
                                   created_at=now,
                                   status='enabled',
                                   data={'foo': 'bar'},
                                   lot_id=1,
                                   framework_id=123))
            db.session.commit()

    def test_get_non_existent_service(self):
        response = self.client.get('/services/9999999999')
        assert_equal(404, response.status_code)

    def test_invalid_service_id(self):
        response = self.client.get('/services/abc123')
        assert_equal(404, response.status_code)

    def test_get_published_service(self):
        response = self.client.get('/services/123-published-456')
        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal("123-published-456", data['services']['id'])

    def test_get_disabled_service(self):
        response = self.client.get('/services/123-disabled-456')
        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal("123-disabled-456", data['services']['id'])

    def test_get_enabled_service(self):
        response = self.client.get('/services/123-enabled-456')
        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal("123-enabled-456", data['services']['id'])

    def test_get_service_returns_supplier_info(self):
        response = self.client.get('/services/123-published-456')
        data = json.loads(response.get_data())
        assert_equal(data['services']['supplierId'], 1)
        assert_equal(data['services']['supplierName'], u'Supplier 1')

    def test_get_service_returns_framework_and_lot_info(self):
        response = self.client.get('/services/123-published-456')
        data = json.loads(response.get_data())

        framework_info = {
            key: value for key, value in data['services'].items()
            if key.startswith('framework') or key.startswith('lot')
        }
        assert framework_info == {
            'frameworkSlug': 'g-cloud-6',
            'frameworkName': 'G-Cloud 6',
            'frameworkFramework': 'g-cloud',
            'frameworkStatus': 'live',
            'lot': 'saas',
            'lotSlug': 'saas',
            'lotName': 'Software as a Service',
        }

    def test_get_service_returns_empty_unavailability_audit_if_published(self):
        # create an audit event for the disabled service
        with self.app.app_context():
            service = Service.query.filter(
                Service.service_id == '123-published-456'
            ).first()
            audit_event = AuditEvent(
                audit_type=AuditTypes.update_service_status,
                db_object=service,
                user='joeblogs',
                data={
                    "supplierId": 1,
                    "newArchivedServiceId": 2,
                    "new_status": "published",
                    "supplierName": "Supplier 1",
                    "serviceId": "123-published-456",
                    "old_status": "disabled",
                    "oldArchivedServiceId": 1
                }
            )
            db.session.add(audit_event)
            db.session.commit()
        response = self.client.get('/services/123-disabled-456')
        data = json.loads(response.get_data())
        assert_equal(data['serviceMadeUnavailableAuditEvent'], None)

    def test_get_service_returns_unavailability_audit_if_disabled(self):
        # create an audit event for the disabled service
        with self.app.app_context():
            service = Service.query.filter(
                Service.service_id == '123-disabled-456'
            ).first()
            audit_event = AuditEvent(
                audit_type=AuditTypes.update_service_status,
                db_object=service,
                user='joeblogs',
                data={
                    "supplierId": 1,
                    "newArchivedServiceId": 2,
                    "new_status": "disabled",
                    "supplierName": "Supplier 1",
                    "serviceId": "123-disabled-456",
                    "old_status": "published",
                    "oldArchivedServiceId": 1
                }
            )
            db.session.add(audit_event)
            db.session.commit()
        response = self.client.get('/services/123-disabled-456')
        data = json.loads(response.get_data())
        assert_equal(data['serviceMadeUnavailableAuditEvent']['type'], 'update_service_status')
        assert_equal(data['serviceMadeUnavailableAuditEvent']['user'], 'joeblogs')
        assert_in('createdAt', data['serviceMadeUnavailableAuditEvent'])
        assert_equal(data['serviceMadeUnavailableAuditEvent']['data']['serviceId'], '123-disabled-456')
        assert_equal(data['serviceMadeUnavailableAuditEvent']['data']['old_status'], 'published')
        assert_equal(data['serviceMadeUnavailableAuditEvent']['data']['new_status'], 'disabled')

    def test_get_service_returns_unavailability_audit_if_published_but_framework_is_expired(self):
        # create an audit event for the disabled service
        with self.app.app_context():
            # get expired framework
            framework = Framework.query.filter(
                Framework.id == 123
            ).first()
            # create an audit event for the framework status change
            audit_event = AuditEvent(
                audit_type=AuditTypes.framework_update,
                db_object=framework,
                user='joeblogs',
                data={
                    "update": {
                        "status": "expired",
                        "clarificationQuestionsOpen": "true"
                    }
                }
            )
            # make a published service use the expired framework
            service = Service.query.filter(
                Service.service_id == '123-published-456'
            ).update({
                'framework_id': 123
            })
            db.session.add(audit_event)
            db.session.commit()
        response = self.client.get('/services/123-published-456')
        data = json.loads(response.get_data())
        assert_equal(data['serviceMadeUnavailableAuditEvent']['type'], 'framework_update')
        assert_equal(data['serviceMadeUnavailableAuditEvent']['user'], 'joeblogs')
        assert_in('createdAt', data['serviceMadeUnavailableAuditEvent'])
        assert_equal(data['serviceMadeUnavailableAuditEvent']['data']['update']['status'], 'expired')

    def test_get_service_returns_correct_unavailability_audit_if_disabled_but_framework_is_expired(self):
        # create an audit event for the disabled service
        with self.app.app_context():
            # get expired framework
            framework = Framework.query.filter(
                Framework.id == 123
            ).first()
            # create an audit event for the framework status change
            audit_event = AuditEvent(
                audit_type=AuditTypes.framework_update,
                db_object=framework,
                user='joeblogs',
                data={
                    "update": {
                        "status": "expired",
                        "clarificationQuestionsOpen": "true"
                    }
                }
            )
            # make a disabled service use the expired framework
            service = Service.query.filter(
                Service.service_id == '123-disabled-456'
            ).update({
                'framework_id': 123
            })
            db.session.add(audit_event)
            db.session.commit()
        response = self.client.get('/services/123-disabled-456')
        data = json.loads(response.get_data())
        assert_equal(data['serviceMadeUnavailableAuditEvent']['type'], 'framework_update')
        assert_equal(data['serviceMadeUnavailableAuditEvent']['user'], 'joeblogs')
        assert_in('createdAt', data['serviceMadeUnavailableAuditEvent'])
        assert_equal(data['serviceMadeUnavailableAuditEvent']['data']['update']['status'], 'expired')
