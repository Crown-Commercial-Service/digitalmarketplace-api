from tests.bases import BaseApplicationTest


class TestStatus(BaseApplicationTest):

    def test_should_return_200_from_elb_status_check(self):
        status_response = self.client.get('/_status?ignore-dependencies')
        assert status_response.status_code == 200
