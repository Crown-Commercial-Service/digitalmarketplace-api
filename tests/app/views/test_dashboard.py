import json

from ..helpers import BaseApplicationTest


class TestDashboard(BaseApplicationTest):
    def stats(self):
        return self.client.get('/dashboard/stats')

    def test_get_stats(self):
        response = self.stats()
        assert response.status_code == 200

        data = json.loads(response.get_data())

        # Check if 'junior' and 'senior' have been stripped from the name
        for role in data['stats']['roles']['top_roles']:
            assert 'junior' not in role['name'].lower()
            assert 'senior' not in role['name'].lower()
