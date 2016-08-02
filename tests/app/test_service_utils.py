import pytest
import mock

from tests.app.helpers import GCloud8ApplicationTest
from app.service_utils import index_service
from app.models import Service


@mock.patch('app.models.url_for')
@mock.patch('app.service_utils.search_api_client')
class TestIndexServices(GCloud8ApplicationTest):

    def test_updating_g_cloud_service_on_live_framework_does_index(self, search_api_client, url_for):
        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            self.setup_dummy_service(
                service_id='10000000001',
                supplier_id=0,
                framework_id=4,  # G-Cloud 7
                lot_id=4,  # scs,
                status='published',
                data={'serviceName': 'service Name'})

            service = Service.query.first()

            index_service(service)
            assert search_api_client.index.called

    def test_updating_g_cloud_service_on_non_live_framework_doesnt_index(self, search_api_client, url_for):
        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            self.setup_dummy_service(
                service_id='10000000001',
                supplier_id=0,
                framework_id=1,  # G-Cloud 6
                lot_id=4,  # scs,
                status='published',
                data={'serviceName': 'service Name'})

            service = Service.query.first()

            index_service(service)
            assert not search_api_client.index.called

    def test_updating_g_cloud_service_on_non_g_cloud_framework_doesnt_index(self, search_api_client, url_for):
        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            self.setup_dummy_service(
                service_id='10000000001',
                supplier_id=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=6,  # digital-specialists
                status='published',
                data={'serviceName': 'service Name'})

            service = Service.query.first()
            index_service(service)
            assert not search_api_client.index.called
