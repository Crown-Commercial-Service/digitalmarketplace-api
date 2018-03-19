from tests.bases import BaseApplicationTest
from sqlalchemy.exc import SQLAlchemyError
import mock
import json


class TestStatus(BaseApplicationTest):
    def setup_method(self, method):
        self._search_api_client_patch = mock.patch('app.status.views.search_api_client', autospec=True)
        self._search_api_client = self._search_api_client_patch.start()
        self._search_api_client.get_status.return_value = {
            'status': 'ok'
        }

    def teardown_method(self, method):
        self._search_api_client_patch.stop()

    def test_should_return_200_from_healthcheck(self):
        status_response = self.client.get('/_status?ignore-dependencies')
        assert status_response.status_code == 200
        assert self._search_api_client.called is False

    @mock.patch('app.status.utils.get_db_version')
    def test_catches_db_error_and_return_500(self, get_db_version):
        get_db_version.side_effect = SQLAlchemyError()
        status_response = self.client.get('/_status')
        assert status_response.status_code == 500

    def test_status_ok(self):
        status_response = self.client.get('/_status')
        assert status_response.status_code == 200

        json_data = json.loads(status_response.get_data().decode('utf-8'))
        assert "{}".format(json_data['search_api_status']['status']) == "ok"

    def test_status_error_in_upstream_api(self):
        self._search_api_client.get_status.return_value = {
            'status': 'error',
            'app_version': None,
            'message': 'Borked'
        }

        response = self.client.get('/_status')
        assert response.status_code == 500

        json_data = json.loads(response.get_data().decode('utf-8'))

        assert "{}".format(json_data['status']) == "error"
        assert "{}".format(json_data['search_api_status']['status']) == "error"

    def test_status_no_response_in_upstream_api(self):
        self._search_api_client.get_status.return_value = None

        response = self.client.get('/_status')
        assert response.status_code == 500

        json_data = json.loads(response.get_data().decode('utf-8'))

        assert "{}".format(json_data['status']) == "error"
        assert json_data.get('search_api_status') == {'status': 'n/a'}
