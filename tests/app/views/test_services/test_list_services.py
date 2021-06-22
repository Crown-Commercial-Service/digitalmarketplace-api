import pendulum

from flask import json
from nose.tools import assert_equal, assert_in, assert_not_in

from app import db, create_app
from tests.app.helpers import BaseApplicationTest, TEST_SUPPLIERS_COUNT


class TestListServices(BaseApplicationTest):
    def setup_services(self):
        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            self.set_framework_status('digital-outcomes-and-specialists', 'live')
            self.setup_dummy_service(
                service_id='10000000001',
                supplier_code=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=5,  # digital-outcomes
                data={"locations": [
                    "London", "Offsite", "Scotland", "Wales"
                ]
                })
            self.setup_dummy_service(
                service_id='10000000002',
                supplier_code=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=6,  # digital-specialists
                data={"agileCoachLocations": ["London", "Offsite", "Scotland", "Wales"]}
            )
            self.setup_dummy_service(
                service_id='10000000003',
                supplier_code=0,
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
            pendulum.parse(
                data['services'][0]['updatedAt'])
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

        data['services'][0]

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

        assert_equal(service['supplierCode'], 0)
        assert_equal(service['supplierName'], 'Supplier 0')

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
        app = create_app('test')

        with app.app_context():
            client = app.test_client()
            self.setup_authorization(app)
            app.config['DM_HTTP_PROTO'] = 'https'
            response = client.get('/', base_url="https://localhost", headers={'X-Forwarded-Proto': 'https'})
            data = json.loads(response.get_data())

        assert data['links']['services.list'].startswith('https://')

    def test_invalid_page_argument(self):
        response = self.client.get('/services?page=a')

        assert_equal(response.status_code, 400)
        assert_in(b'Invalid page argument', response.get_data())

    def test_invalid_supplier_code_argument(self):
        response = self.client.get('/services?supplier_code=a')

        assert_equal(response.status_code, 400)
        assert_in(b'Invalid supplier_code', response.get_data())

    def test_non_existent_supplier_code_argument(self):
        response = self.client.get('/services?supplier_code=54321')

        assert_equal(response.status_code, 404)

    def test_supplier_code_filter(self):
        self.setup_dummy_services_including_unpublished(15)

        response = self.client.get('/services?supplier_code=1')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(
            list([s for s in data['services'] if s['supplierCode'] == 1]),
            data['services']
        )

    def test_supplier_code_with_no_services_filter(self):
        self.setup_dummy_services_including_unpublished(15)

        response = self.client.get(
            '/services?supplier_code=%d' % TEST_SUPPLIERS_COUNT
        )
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(
            list(),
            data['services']
        )

    def test_supplier_should_get_all_service_on_one_page(self):
        self.setup_dummy_services_including_unpublished(21)

        response = self.client.get('/services?supplier_code=1')
        data = json.loads(response.get_data())

        assert_not_in('next', data['links'])
        assert_equal(len(data['services']), 7)

    def test_unknown_supplier_code(self):
        self.setup_dummy_services_including_unpublished(15)
        response = self.client.get('/services?supplier_code=100')

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
        assert data['error'] == 'ValidationError: Lot must be specified to filter by location'

    def test_can_only_filter_by_role_for_specialists_lot(self):
        self.setup_services()
        response = self.client.get('/services?lot=digital-outcomes&role=agileCoach')
        data = json.loads(response.get_data())

        assert response.status_code == 400
        assert data['error'] == 'ValidationError: Role only applies to Digital Specialists lot'

    def test_role_required_for_digital_specialists_location_query(self):
        self.setup_services()
        response = self.client.get('/services?lot=digital-specialists&location=Wales')
        data = json.loads(response.get_data())

        assert response.status_code == 400
        assert data['error'] == 'ValidationError: Role must be specified for Digital Specialists'
