from flask import json
from nose.tools import (assert_equal,
                        assert_false,
                        assert_is_not_none)

from app.models import (Service,
                        Supplier,
                        Address)
import mock
from app import db
from tests.app.helpers import BaseApplicationTest

from dmapiclient import HTTPError


@mock.patch('app.service_utils.search_api_client')
class TestShouldCallSearchApiOnPutToCreateService(BaseApplicationTest):
    def setup(self):
        super(TestShouldCallSearchApiOnPutToCreateService, self).setup()

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
