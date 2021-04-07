import json
from pendulum import create as datetime

from tests.app.helpers import BaseApplicationTest
from tests import example_listings

from app.models import db, Lot, Brief, WorkOrder


class BaseWorkOrderTest(BaseApplicationTest):
    def setup(self):
        super(BaseWorkOrderTest, self).setup()

        with self.app.app_context():
            self.setup_dummy_suppliers(2)
            brief = Brief(
                data=example_listings.brief_data().example(),
                published_at=datetime(2016, 1, 1), framework_id=5, lot=Lot.query.get(5)
            )

            db.session.add(brief)
            db.session.commit()

            self.brief_id = brief.id

    def setup_dummy_work_order(self, brief_id=None, supplier_code=0, data=None):
        if data is None:
            data = self.work_order_data
        with self.app.app_context():
            brief = Brief(
                data=example_listings.brief_data().example(),
                published_at=datetime(2016, 1, 1), framework_id=5, lot=Lot.query.get(5)
            )

            db.session.add(brief)
            db.session.commit()

            work_order = WorkOrder(
                data=data,
                supplier_code=supplier_code,
                brief_id=brief_id or brief.id
            )

            db.session.add(work_order)
            db.session.commit()

            return work_order.id, brief.id

    def create_work_order(self, data):
        return self.client.post(
            '/work-orders',
            data=json.dumps({
                'updated_by': 'test@example.com',
                'workOrder': data,
            }),
            content_type='application/json'
        )

    def patch_work_order(self, work_order_id, data):
        return self.client.patch(
            '/work-orders/{}'.format(work_order_id),
            data=json.dumps({
                'updated_by': 'test@example.com',
                'workOrder': data,
            }),
            content_type='application/json'
        )

    def get_work_order(self, work_order_id):
        return self.client.get('/work-orders/{}'.format(work_order_id))

    def list_work_orders(self, **parameters):
        return self.client.get('/work-orders', query_string=parameters)

    @property
    def work_order_data(self):
        return {'foo': 'bar'}


class TestCreateWorkOrder(BaseWorkOrderTest):
    endpoint = '/work-orders'
    method = 'post'

    def test_create_new_work_order(self):
        res = self.create_work_order(
            dict(self.work_order_data, briefId=self.brief_id, supplierCode=0)
        )

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 201, data
        assert data['workOrder']['supplierName'] == 'Supplier 0'
        assert data['workOrder']['briefId'] == self.brief_id

    def test_cannot_create_work_order_with_empty_json(self):
        res = self.client.post(
            '/work-orders',
            data=json.dumps({
                'updated_by': 'test@example.com',
            }),
            content_type='application/json'
        )

        assert res.status_code == 400

    def test_cannot_create_work_order_without_supplier_code(self):
        res = self.create_work_order({
            'briefId': self.brief_id
        })

        assert res.status_code == 400
        assert 'supplierCode' in res.get_data(as_text=True)

    def test_cannot_create_work_order_without_brief_id(self):
        res = self.create_work_order({
            'supplierCode': 0
        })

        assert res.status_code == 400
        assert 'briefId' in res.get_data(as_text=True)

    def test_cannot_create_work_order_with_non_integer_supplier_code(self):
        res = self.create_work_order({
            'briefId': self.brief_id,
            'supplierCode': 'not a number',
        })

        assert res.status_code == 400
        assert 'Invalid supplier Code' in res.get_data(as_text=True)

    def test_cannot_create_work_order_with_non_integer_brief_id(self):
        res = self.create_work_order({
            'briefId': 'not a number',
            'supplierCode': 0,
        })

        assert res.status_code == 400
        assert 'Invalid opportunity ID' in res.get_data(as_text=True)

    def test_cannot_create_work_order_when_brief_doesnt_exist(self):
        res = self.create_work_order({
            'briefId': self.brief_id + 100,
            'supplierCode': 0
        })

        assert res.status_code == 400
        assert 'Invalid opportunity ID' in res.get_data(as_text=True)

    def test_cannot_create_work_order_when_supplier_doesnt_exist(self):
        res = self.create_work_order({
            'briefId': self.brief_id,
            'supplierCode': 999
        })

        assert res.status_code == 400
        assert 'Invalid supplier Code' in res.get_data(as_text=True)

    def test_cannot_respond_to_a_brief_that_isnt_closed(self):
        with self.app.app_context():
            brief = Brief(
                data={}, status='draft', framework_id=5, lot=Lot.query.get(5)
            )
            db.session.add(brief)
            db.session.commit()

            brief_id = brief.id

        res = self.create_work_order({
            'briefId': brief_id,
            'supplierCode': 0
        })

        assert res.status_code == 400
        assert "Opportunity must be closed" in res.get_data(as_text=True)

    def test_cannot_create_work_order_for_a_brief_more_than_once(self):
        self.create_work_order(
            dict(self.work_order_data, briefId=self.brief_id, supplierCode=0)
        )

        res = self.create_work_order(
            dict(self.work_order_data, briefId=self.brief_id, supplierCode=1)
        )

        assert res.status_code == 400, res.get_data(as_text=True)
        assert 'Work order already exists' in res.get_data(as_text=True)


class TestUpdateWorkOrder(BaseWorkOrderTest):

    def setup(self):
        super(TestUpdateWorkOrder, self).setup()
        self.work_order_id, _ = self.setup_dummy_work_order(
            brief_id=self.brief_id,
            supplier_code=0,
            data=self.work_order_data
        )

    def test_patch_existing_order(self):
        work_order_data = self.work_order_data
        work_order_data['foo'] = 'baz'

        res = self.patch_work_order(
            work_order_id=self.work_order_id,
            data=work_order_data
        )

        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))
        assert data['workOrder']['supplierName'] == 'Supplier 0'
        assert data['workOrder']['briefId'] == self.brief_id
        assert data['workOrder']['foo'] == 'baz'

    def test_empty_patch(self):
        res = self.patch_work_order(
            work_order_id=self.work_order_id,
            data={}
        )

        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))
        assert data['workOrder']['supplierName'] == 'Supplier 0'
        assert data['workOrder']['briefId'] == self.brief_id
        assert data['workOrder']['foo'] == self.work_order_data['foo']

    def test_patch_missing_order(self):
        res = self.patch_work_order(
            work_order_id=9,
            data={}
        )

        assert res.status_code == 404

    def test_malformed_request(self):
        res = self.client.patch('/work-orders/1', data={'notAWorkOrder': 'no'})
        assert res.status_code == 400


class TestGetWorkOrder(BaseWorkOrderTest):
    def setup(self):
        super(TestGetWorkOrder, self).setup()

        self.work_order_id, _ = self.setup_dummy_work_order()

    def test_get_work_order(self):
        res = self.get_work_order(self.work_order_id)

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['workOrder']['id'] == self.work_order_id
        assert data['workOrder']['supplierCode'] == 0

    def test_get_missing_work_order_returns_404(self):
        res = self.get_work_order(999)

        assert res.status_code == 404


class TestListworkOrders(BaseWorkOrderTest):
    def test_list_empty_work_orders(self):
        res = self.list_work_orders()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['workOrders'] == []
        assert 'self' in data['links'], data

    def test_list_work_orders(self):
        for i in range(3):
            self.setup_dummy_work_order()

        res = self.list_work_orders()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['workOrders']) == 3
        assert 'self' in data['links']

    def test_list_work_orders_pagination(self):
        for i in range(8):
            self.setup_dummy_work_order()

        res = self.list_work_orders()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['workOrders']) == 5
        assert 'next' in data['links']

        res = self.list_work_orders(page=2)
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['workOrders']) == 3
        assert 'prev' in data['links']

    def test_results_per_page(self):
        for i in range(8):
            self.setup_dummy_work_order()

        response = self.client.get('/work-orders?per_page=2')
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert 'workOrders' in data
        assert len(data['workOrders']) == 2

    def test_list_work_orders_for_supplier_code(self):
        for i in range(3):
            self.setup_dummy_work_order(supplier_code=0)
            self.setup_dummy_work_order(supplier_code=1)

        res = self.list_work_orders(supplier_code=1)
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['workOrders']) == 3
        assert all(br['supplierCode'] == 1 for br in data['workOrders'])
        assert 'self' in data['links']

    def test_list_work_orders_for_brief_id(self):
        _, brief_id = self.setup_dummy_work_order()
        for i in range(3):
            self.setup_dummy_work_order()

        res = self.list_work_orders(brief_id=brief_id)
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['workOrders']) == 1
        assert 'self' in data['links']

    def test_cannot_list_work_orders_for_non_integer_brief_id(self):
        res = self.list_work_orders(brief_id="not-valid")
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == 'Invalid brief_id: not-valid'

    def test_cannot_list_work_orders_for_non_integer_supplier_code(self):
        res = self.list_work_orders(supplier_code="not-valid")
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == 'Invalid supplier_code: not-valid'
