import mock

from tests.bases import BaseApplicationTest
from app.service_utils import index_service
from app.models import Service, Framework


@mock.patch('app.service_utils.index_object', autospec=True)
class TestIndexServices(BaseApplicationTest):

    def test_live_g_cloud_8_published_service_is_indexed(
            self, index_object, live_g8_framework
    ):
        with self.app.app_context():
            g8 = Framework.query.filter(Framework.slug == 'g-cloud-8').first()

            with mock.patch.object(Service, "serialize", return_value={'serialized': 'object'}):
                service = Service(status='published', framework=g8)
                index_service(service)

            index_object.assert_called_once_with(
                framework='g-cloud-8',
                object_type='services',
                object_id=None,
                serialized_object={'serialized': 'object'},
            )

    def test_live_g_cloud_8_enabled_service_is_not_indexed(
            self, index_object, live_g8_framework
    ):
        with self.app.app_context():
            g8 = Framework.query.filter(Framework.slug == 'g-cloud-8').first()

            with mock.patch.object(Service, "serialize"):
                service = Service(status='enabled', framework=g8)
                index_service(service)

            assert not index_object.called

    def test_live_dos_published_service_is_not_indexed(self, index_object, live_dos_framework):
        with self.app.app_context():
            dos = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()

            with mock.patch.object(Service, "serialize"):
                service = Service(status='published', framework=dos)
                index_service(service)

            assert not index_object.called

    def test_expired_g_cloud_6_published_service_is_not_indexed(self, index_object, expired_g6_framework):
        with self.app.app_context():
            g6 = Framework.query.filter(Framework.slug == 'g-cloud-6').first()

            with mock.patch.object(Service, "serialize"):
                service = Service(status='published', framework=g6)
                index_service(service)

            assert not index_object.called
