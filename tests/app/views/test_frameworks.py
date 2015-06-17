from __future__ import absolute_import

from flask import json
from nose.tools import assert_equal

from ..helpers import BaseApplicationTest


class TestListFrameworks(BaseApplicationTest):
    def test_all_frameworks_are_returned(self):
        with self.app.app_context():
            response = self.client.get('/frameworks')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
            assert_equal(len(data['frameworks']), 3)
