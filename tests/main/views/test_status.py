from tests.bases import BaseApplicationTest

from nose.tools import assert_equal


class TestStatus(BaseApplicationTest):

    def test_should_return_200_from_elb_status_check(self):
        status_response = self.client.get('/_status?ignore-dependencies')
        assert_equal(200, status_response.status_code)
