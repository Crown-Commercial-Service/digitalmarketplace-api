from tests.app.helpers import BaseApplicationTest
from flask import json

from nose.tools import assert_equal


class TestDraftServices(BaseApplicationTest):

    def test_reject_invalid_service_id_on_post(self):
        res = self.client.post(
            '/services/invalid-id!/draft',
            data=json.dumps({'key': 'value'}),
            content_type='application/json')

        assert_equal(res.status_code, 400)

    def test_reject_invalid_service_id_on_put(self):
        res = self.client.put('/services/invalid-id!/draft')

        assert_equal(res.status_code, 400)

    def test_reject_invalid_service_id_on_get(self):
        res = self.client.get('/services/invalid-id!/draft')

        assert_equal(res.status_code, 400)