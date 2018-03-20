from flask import json
from datetime import datetime
from nose.tools import assert_equal

from app.models import (Region,
                        ServiceType,
                        ServiceSubType,
                        ServiceTypePriceCeiling,
                        Supplier,
                        Address)
from app import db
from tests.app.helpers import BaseApplicationTest


class TestAddServiceTypePriceCeilings(BaseApplicationTest):
    endpoint = '/service-type-price-ceilings'
    method = 'post'

    def setup(self):
        super(TestAddServiceTypePriceCeilings, self).setup()

        with self.app.app_context():
            now = datetime.utcnow()
            supplier = Supplier(id="1",
                                code="1",
                                name=u"Supplier 1",
                                addresses=[Address(address_line="{} Dummy Street 1",
                                                   suburb="Dummy",
                                                   state="ZZZ",
                                                   postal_code="0000",
                                                   country='Australia')])
            db.session.add(supplier)

            service_type = ServiceType(id=1,
                                       category_id=10,
                                       name="Ergonomic review",
                                       framework_id=8,
                                       lot_id=11,
                                       created_at=now,
                                       updated_at=now,
                                       fee_type="Fixed")
            db.session.add(service_type)

            service_type = ServiceType(id=2,
                                       category_id=10,
                                       name="Add",
                                       framework_id=8,
                                       lot_id=11,
                                       created_at=now,
                                       updated_at=now,
                                       fee_type="Fixed")
            db.session.add(service_type)

            service_sub_type = ServiceSubType(id=1,
                                              name="Psychological",
                                              created_at=now,
                                              updated_at=now)
            db.session.add(service_sub_type)

            region = Region(id=1,
                            name="ACT",
                            state="ACT",
                            created_at=now,
                            updated_at=now)
            db.session.add(region)
            db.session.commit()

            service_type_price_ceiling = ServiceTypePriceCeiling(supplier_code=1,
                                                                 region_id=1,
                                                                 service_type_id=1,
                                                                 sub_service_id=1,
                                                                 price=20,
                                                                 created_at=now,
                                                                 updated_at=now)
            db.session.add(service_type_price_ceiling)
            db.session.commit()

    def test_can_add_price_ceilings(self):
        response = self.client.post(
            self.endpoint,
            data=json.dumps({'price': {
                'supplier_name': "Supplier 1",
                'service_name': "Add",
                'sub_service': "Psychological",
                'region_name': "ACT",
                'state': "ACT",
                'price': 20
            }}),
            content_type='application/json')

        data = json.loads(response.get_data())
        assert_equal(response.status_code, 201)
        assert_equal(data.get('msg'), "Added price ceiling record.")

    def test_can_update_price_ceilings(self):
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
        assert_equal(response.status_code, 201)
        assert_equal(data.get('msg'), "Updated price ceiling record.")

    def test_can_detect_same_price_ceilings(self):
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
        assert_equal(response.status_code, 200)
        assert_equal(data.get('msg'), "No changes made. Price is the same.")
