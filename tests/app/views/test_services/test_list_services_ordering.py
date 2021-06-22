import pendulum

from flask import json
from nose.tools import assert_equal
from app.models import Service, Supplier, Address
from app import db
from tests.app.helpers import BaseApplicationTest


class TestListServicesOrdering(BaseApplicationTest):
    def setup_services(self):
        with self.app.app_context():
            self.app.config['DM_API_SERVICES_PAGE_SIZE'] = 10
            now = pendulum.now('UTC')

            g5_saas = self.load_example_listing("G5")
            g5_paas = self.load_example_listing("G5")
            g6_paas_2 = self.load_example_listing("G6-PaaS")
            g6_iaas_1 = self.load_example_listing("G6-IaaS")
            g6_paas_1 = self.load_example_listing("G6-PaaS")
            g6_saas = self.load_example_listing("G6-SaaS")
            g6_iaas_2 = self.load_example_listing("G6-IaaS")

            db.session.add(
                Supplier(code=1,
                         name="Supplier 1",
                         description="",
                         summary="",
                         addresses=[Address(address_line="{} Dummy Street 1",
                                            suburb="Dummy",
                                            state="ZZZ",
                                            postal_code="0000",
                                            country='Australia')],
                         contacts=[],
                         references=[],
                         prices=[],
                         )
            )

            def insert_service(listing, service_id, lot_id, framework_id):
                db.session.add(Service(service_id=service_id,
                                       supplier_code=1,
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

        response = self.client.get('/services?supplier_code=1')
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

        response = self.client.get('/services')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal([d['id'] for d in data['services']], [
            '123-g5-paas',
            '123-g5-saas',
            '123-g6-iaas-1',
            '123-g6-iaas-2',
            '123-g6-paas-1',
            '123-g6-paas-2',
            '123-g6-saas',
        ])
