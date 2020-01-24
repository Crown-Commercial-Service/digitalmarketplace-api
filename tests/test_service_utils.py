import mock

import pytest
from werkzeug.exceptions import BadRequest

from tests.bases import BaseApplicationTest
from app.service_utils import index_service, delete_service_from_index, validate_and_return_service_request
from app.models import Service, Framework


@mock.patch('app.service_utils.get_json_from_request')
class TestValidateAndReturnServiceJSON(BaseApplicationTest):

    def test_service_request_has_required_keys(self, get_json_from_request):
        get_json_from_request.return_value = {'foo': 'bar'}
        with pytest.raises(BadRequest) as exc:
            validate_and_return_service_request('any_service_id')
        assert exc.value.code == 400
        assert str(exc.value) == "400 Bad Request: Invalid JSON must have 'services' keys"

    def test_service_request_with_id_must_match_service_id(self, get_json_from_request):
        get_json_from_request.return_value = {
            'services': {
                'id': 12345
            }
        }
        with pytest.raises(BadRequest) as exc:
            validate_and_return_service_request('wrong_service_id')
        assert exc.value.code == 400
        assert str(exc.value) == "400 Bad Request: id parameter must match id in data"

    def test_service_request_happy_path(self, get_json_from_request):
        get_json_from_request.return_value = {
            'services': {
                'foo': 'bar',
                'baz': 'bork'
            }
        }
        assert validate_and_return_service_request('any_service_id') == {
            'foo': 'bar',
            'baz': 'bork'
        }


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

    @pytest.mark.parametrize("wait_for_response,expected_client_wait_for_response", (
        (None, True),
        (True, True),
        (False, False),
    ))
    def test_live_g_cloud_8_published_service_is_deleted(
        self,
        search_api_client,
        live_g8_framework,
        wait_for_response,
        expected_client_wait_for_response,
    ):
        g8 = Framework.query.filter(Framework.slug == 'g-cloud-8').first()

        with mock.patch.object(Service, "serialize", return_value={'serialized': 'object'}):
            service = Service(status='published', framework=g8)
            delete_service_from_index(service, **({} if wait_for_response is None else {
                "wait_for_response": wait_for_response,
            }))

        search_api_client.delete.mock_calls == [
            mock.call(
                index='g-cloud-8',
                service_id=None,
                client_wait_for_response=expected_client_wait_for_response,
            )
        ]

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
