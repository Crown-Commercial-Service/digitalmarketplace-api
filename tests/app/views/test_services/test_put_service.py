import pendulum
from datetime import timedelta

from flask import json
from nose.tools import (assert_equal,
                        assert_in,
                        assert_true,
                        assert_almost_equal,
                        assert_not_in)

from app.models import (Service,
                        Supplier,
                        Address)
import mock
from app import db
from tests.app.helpers import (BaseApplicationTest,
                               JSONUpdateTestMixin)


class TestPutService(BaseApplicationTest, JSONUpdateTestMixin):
    method = "put"
    endpoint = "/services/1234567890123456"

    def setup(self):
        super(TestPutService, self).setup()

        payload = self.load_example_listing("G6-IaaS")
        del payload['id']
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
            now = pendulum.now('UTC')

            response = self.client.get("/services/1234567890123456")
            service = json.loads(response.get_data())["services"]

            assert_equal(
                service["id"],
                payload['id'])

            assert_equal(
                service["supplierCode"],
                payload['supplierCode'])

            assert self.string_to_time(service["createdAt"]) == \
                self.string_to_time(payload['createdAt'])

            assert_almost_equal(
                self.string_to_time(service["updatedAt"]),
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
            assert_equal(data['auditEvents'][0]['data']['supplierCode'],
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
            now = pendulum.now('UTC')
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

    def test_add_a_service_with_unknown_supplier_code(self):
        with self.app.app_context():
            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "6543210987654321"
            payload['supplierCode'] = 100
            response = self.client.put(
                '/services/6543210987654321',
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': payload}
                ),
                content_type='application/json')

            assert_equal(response.status_code, 400)
            assert_in("Invalid supplier Code '100'", json.loads(response.get_data())['error'])

    def test_supplier_name_in_service_data_is_shadowed(self):

        with self.app.app_context():
            payload = self.load_example_listing("G6-IaaS")
            payload['id'] = "1234567890123456"
            payload['supplierCode'] = 1
            payload['supplierName'] = 'New Name'

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
            assert_equal(data['services']['supplierName'], 'Supplier 1')
