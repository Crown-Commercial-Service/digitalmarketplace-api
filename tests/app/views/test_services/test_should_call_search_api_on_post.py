import pendulum

from flask import json
from nose.tools import (assert_equal,
                        assert_false)

from app.models import (Service,
                        Supplier,
                        Address)
import mock
from app import db
from tests.app.helpers import BaseApplicationTest

from sqlalchemy.exc import IntegrityError
from dmapiclient import HTTPError


@mock.patch('app.service_utils.search_api_client')
class TestShouldCallSearchApiOnPost(BaseApplicationTest):
    def setup(self):
        super(TestShouldCallSearchApiOnPost, self).setup()

        now = pendulum.now('UTC')
        payload = self.load_example_listing("G6-IaaS")
        g4_payload = self.load_example_listing("G4")
        with self.app.app_context():
            db.session.add(
                Supplier(code=1, name="Supplier 1",
                         addresses=[Address(address_line="{} Dummy Street 1",
                                            suburb="Dummy",
                                            state="ZZZ",
                                            postal_code="0000",
                                            country='Australia')])
            )
            db.session.add(Service(service_id="1234567890123456",
                                   supplier_code=1,
                                   updated_at=now,
                                   status='published',
                                   created_at=now,
                                   lot_id=3,
                                   framework_id=1,
                                   data=payload))
            db.session.add(Service(service_id="4-G2-0123-456",
                                   supplier_code=1,
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
