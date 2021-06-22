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

from dmapiclient import HTTPError


class TestShouldCallSearchApiOnPostStatusUpdate(BaseApplicationTest):
    def setup(self):
        super(TestShouldCallSearchApiOnPostStatusUpdate, self).setup()

        now = pendulum.now('UTC')
        self.services = {}

        valid_statuses = [
            'published',
            'enabled',
            'disabled'
        ]

        with self.app.app_context():
            db.session.add(
                Supplier(code=1, name="Supplier 1",
                         addresses=[Address(address_line="{} Dummy Street 1",
                                            suburb="Dummy",
                                            state="ZZZ",
                                            postal_code="0000",
                                            country='Australia')])
            )

            for index, status in enumerate(valid_statuses):
                payload = self.load_example_listing("G6-IaaS")

                # give each service a different id.
                new_id = int(payload['id']) + index
                payload['id'] = "{}".format(new_id)

                self.services[status] = payload

                db.session.add(Service(service_id=self.services[status]['id'],
                                       supplier_code=1,
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
