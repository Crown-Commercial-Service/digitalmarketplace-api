from flask import json
from pendulum import Pendulum
from nose.tools import assert_equal

from app.models import (Region,
                        ServiceType,
                        ServiceSubType,
                        ServiceTypePrice,
                        ServiceTypePriceCeiling,
                        Supplier,
                        Address)
from app import db
from tests.app.helpers import BaseApplicationTest


class TestAddServiceTypePrice(BaseApplicationTest):
    endpoint = '/service-type-prices'
    method = 'post'

    def setup(self):
        super(TestAddServiceTypePrice, self).setup()

        with self.app.app_context():
            now = Pendulum.utcnow()
            db.session.add(Supplier(id="1",
                                    code="1",
                                    name=u"Supplier 1",
                                    addresses=[Address(address_line="{} Dummy Street 1",
                                                       suburb="Dummy",
                                                       state="ZZZ",
                                                       postal_code="0000",
                                                       country='Australia')]))
            db.session.add(Supplier(id="2",
                                    code="2",
                                    name=u"Supplier 2",
                                    addresses=[Address(address_line="{} Dummy Street 2",
                                                       suburb="Dummy",
                                                       state="ZZZ",
                                                       postal_code="0000",
                                                       country='Australia')]))

            db.session.add(ServiceType(id=1,
                                       category_id=10,
                                       name="Ergonomic review",
                                       framework_id=8,
                                       lot_id=11,
                                       created_at=now,
                                       updated_at=now,
                                       fee_type="Fixed"))

            db.session.add(ServiceType(id=2,
                                       category_id=10,
                                       name="Add",
                                       framework_id=8,
                                       lot_id=11,
                                       created_at=now,
                                       updated_at=now,
                                       fee_type="Fixed"))

            db.session.add(ServiceSubType(id=1,
                                          name="Psychological",
                                          created_at=now,
                                          updated_at=now))

            db.session.add(Region(id=1,
                                  name="ACT",
                                  state="ACT",
                                  created_at=now,
                                  updated_at=now))

            db.session.add(Region(id=2,
                                  name="NSW Region",
                                  state="NSW",
                                  created_at=now,
                                  updated_at=now))
            db.session.commit()

            db.session.add(ServiceTypePriceCeiling(id=1,
                                                   supplier_code=1,
                                                   region_id=1,
                                                   service_type_id=1,
                                                   sub_service_id=1,
                                                   price=20,
                                                   created_at=now,
                                                   updated_at=now))
            db.session.add(ServiceTypePriceCeiling(id=2,
                                                   supplier_code=1,
                                                   region_id=2,
                                                   service_type_id=1,
                                                   sub_service_id=1,
                                                   price=20,
                                                   created_at=now,
                                                   updated_at=now))
            db.session.add(ServiceTypePriceCeiling(id=3,
                                                   supplier_code=2,
                                                   region_id=1,
                                                   service_type_id=1,
                                                   sub_service_id=1,
                                                   price=21,
                                                   created_at=now,
                                                   updated_at=now))
            db.session.commit()

            db.session.add(ServiceTypePrice(supplier_code=1,
                                            region_id=1,
                                            service_type_id=1,
                                            sub_service_id=1,
                                            price=20,
                                            date_from=Pendulum(2016, 1, 1),
                                            date_to=Pendulum(2050, 1, 1),
                                            created_at=now,
                                            updated_at=now,
                                            service_type_price_ceiling_id=1))

            db.session.add(ServiceTypePrice(supplier_code=2,
                                            region_id=1,
                                            service_type_id=1,
                                            sub_service_id=1,
                                            price=20,
                                            date_from=Pendulum(2016, 1, 1),
                                            date_to=Pendulum(2050, 1, 1),
                                            created_at=now.subtract(weeks=1),
                                            updated_at=now.subtract(weeks=1),
                                            service_type_price_ceiling_id=3))
            db.session.add(ServiceTypePrice(supplier_code=2,
                                            region_id=1,
                                            service_type_id=1,
                                            sub_service_id=1,
                                            price=21,
                                            date_from=Pendulum(2016, 1, 1),
                                            date_to=Pendulum(2050, 1, 1),
                                            created_at=now,
                                            updated_at=now,
                                            service_type_price_ceiling_id=3))
            db.session.commit()

    def test_can_add_price(self):
        response = self.client.post(
            self.endpoint,
            data=json.dumps({'price': {
                'supplier_name': "Supplier 1",
                'service_name': "Ergonomic review",
                'sub_service': "Psychological",
                'region_name': "NSW Region",
                'state': "NSW",
                'price': 20
            }}),
            content_type='application/json')

        data = json.loads(response.get_data())
        assert_equal(data.get('msg'), "Added price")
        assert_equal(response.status_code, 201)

    def test_can_detect_no_price_change_for_multiple_current_date(self):
        response = self.client.post(
            self.endpoint,
            data=json.dumps({'price': {
                'supplier_name': "Supplier 2",
                'service_name': "Ergonomic review",
                'sub_service': "Psychological",
                'region_name': "ACT",
                'state': "ACT",
                'price': 21
            }}),
            content_type='application/json')

        data = json.loads(response.get_data())
        assert_equal(data.get('msg'), "No changes made. Price is the same.")
        assert_equal(response.status_code, 200)

    def test_can_add_price_for_multiple_current_date(self):
        response = self.client.post(
            self.endpoint,
            data=json.dumps({'price': {
                'supplier_name': "Supplier 2",
                'service_name': "Ergonomic review",
                'sub_service': "Psychological",
                'region_name': "ACT",
                'state': "ACT",
                'price': 20
            }}),
            content_type='application/json')

        data = json.loads(response.get_data())
        assert_equal(data.get('msg'), "Expired current price. Added new price")
        assert_equal(response.status_code, 201)

    def test_can_update_price(self):
        # update normally
        response = self.client.post(
            self.endpoint,
            data=json.dumps({'price': {
                'supplier_name': "Supplier 1",
                'service_name': "Ergonomic review",
                'sub_service': "Psychological",
                'region_name': "ACT",
                'state': "ACT",
                'price': 21
            }}),
            content_type='application/json')

        data = json.loads(response.get_data())
        assert_equal(data.get('msg'), "Expired current price. Added new price")
        assert_equal(response.status_code, 201)

        # update future record
        response = self.client.post(
            self.endpoint,
            data=json.dumps({'price': {
                'supplier_name': "Supplier 1",
                'service_name': "Ergonomic review",
                'sub_service': "Psychological",
                'region_name': "ACT",
                'state': "ACT",
                'price': 22
            }}),
            content_type='application/json')

        data = json.loads(response.get_data())
        assert_equal(data.get('msg'), "Updated future price record.")
        assert_equal(response.status_code, 201)

        # update future record with same price
        response = self.client.post(
            self.endpoint,
            data=json.dumps({'price': {
                'supplier_name': "Supplier 1",
                'service_name': "Ergonomic review",
                'sub_service': "Psychological",
                'region_name': "ACT",
                'state': "ACT",
                'price': 22
            }}),
            content_type='application/json')

        data = json.loads(response.get_data())
        assert_equal(data.get('msg'), "No changes made. Price is the same.")
        assert_equal(response.status_code, 200)

    def test_can_detect_same_price(self):
        response = self.client.post(
            self.endpoint,
            data=json.dumps({'price': {
                'supplier_name': "Supplier 1",
                'service_name': "Ergonomic review",
                'sub_service': "Psychological",
                'region_name': "ACT",
                'state': "ACT",
                'price': 20
            }}),
            content_type='application/json')

        data = json.loads(response.get_data())
        assert_equal(data.get('msg'), "No changes made. Price is the same.")
        assert_equal(response.status_code, 200)
