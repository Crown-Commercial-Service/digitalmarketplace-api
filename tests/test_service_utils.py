import mock

import pytest

from tests.bases import BaseApplicationTest
from app.service_utils import index_service, delete_service_from_index
from app.models import Service, Framework


@mock.patch('app.service_utils.index_object', autospec=True)
class TestIndexServices(BaseApplicationTest):

    @pytest.mark.parametrize("wait_for_response", (False, True,))
    def test_live_g_cloud_8_published_service_is_indexed(
            self, index_object, live_g8_framework, wait_for_response,
    ):
        g8 = Framework.query.filter(Framework.slug == 'g-cloud-8').first()

        with mock.patch.object(Service, "serialize", return_value={'serialized': 'object'}):
            service = Service(status='published', framework=g8)
            index_service(service, wait_for_response=wait_for_response)

        assert index_object.mock_calls == [
            mock.call(
                framework='g-cloud-8',
                doc_type='services',
                object_id=None,
                serialized_object={'serialized': 'object'},
                wait_for_response=wait_for_response,
            ),
        ]

    def test_live_g_cloud_8_enabled_service_is_not_indexed(
            self, index_object, live_g8_framework
    ):
        g8 = Framework.query.filter(Framework.slug == 'g-cloud-8').first()

        with mock.patch.object(Service, "serialize"):
            service = Service(status='enabled', framework=g8)
            index_service(service)

        assert not index_object.called

    def test_live_dos_published_service_is_not_indexed(self, index_object, live_dos_framework):
        dos = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()

        with mock.patch.object(Service, "serialize"):
            service = Service(status='published', framework=dos)
            index_service(service)

        assert not index_object.called

    def test_expired_g_cloud_6_published_service_is_not_indexed(self, index_object, expired_g6_framework):
        g6 = Framework.query.filter(Framework.slug == 'g-cloud-6').first()

        with mock.patch.object(Service, "serialize"):
            service = Service(status='published', framework=g6)
            index_service(service)

        assert not index_object.called


@mock.patch('app.service_utils.search_api_client', autospec=True)
class TestDeleteServiceFromIndex(BaseApplicationTest):

    def test_live_g_cloud_8_published_service_is_deleted(self, search_api_client, live_g8_framework):
        g8 = Framework.query.filter(Framework.slug == 'g-cloud-8').first()

        with mock.patch.object(Service, "serialize", return_value={'serialized': 'object'}):
            service = Service(status='published', framework=g8)
            delete_service_from_index(service)

        search_api_client.delete.assert_called_once_with(
            index='g-cloud-8',
            service_id=None
        )

    def test_live_dos_service_is_not_deleted(self, search_api_client, live_dos_framework):
        dos = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()

        with mock.patch.object(Service, "serialize"):
            service = Service(status='published', framework=dos)
            delete_service_from_index(service)

        assert search_api_client.delete.called is False

    def test_expired_g_cloud_6_service_is_not_deleted(self, search_api_client, expired_g6_framework):
        g6 = Framework.query.filter(Framework.slug == 'g-cloud-6').first()

        with mock.patch.object(Service, "serialize"):
            service = Service(status='published', framework=g6)
            delete_service_from_index(service)

        assert search_api_client.delete.called is False
