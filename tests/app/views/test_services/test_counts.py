from flask import json
from tests.app.helpers import BaseApplicationTest


class TestCounts(BaseApplicationTest):

    def test_get_roles(self):
        response = self.client.get('/roles/count')
        assert response.status_code == 200

        data = json.loads(response.get_data())

        # Check if 'junior' and 'senior' have been stripped from the name
        for role in data['roles']['top_roles']:
            assert 'junior' not in role['name'].lower()
            assert 'senior' not in role['name'].lower()
