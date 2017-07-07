from tests.bases import BaseApplicationTest
from sqlalchemy.exc import SQLAlchemyError
import mock


class TestStatus(BaseApplicationTest):

    def test_should_return_200_from_elb_status_check(self):
        status_response = self.client.get('/_status?ignore-dependencies')
        assert status_response.status_code == 200

    @mock.patch('app.status.utils.get_db_version')
    def test_catches_db_error_and_return_500(self, get_db_version):
        get_db_version.side_effect = SQLAlchemyError()
        status_response = self.client.get('/_status')
        assert status_response.status_code == 500
