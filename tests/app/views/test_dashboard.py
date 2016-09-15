import json

from ..helpers import BaseApplicationTest


class TestDashboard(BaseApplicationTest):

    def test_get_buyers(self):
        response = self.client.get('/dashboard/buyers')
        assert response.status_code == 200

    def test_get_suppliers(self):
        response = self.client.get('/dashboard/suppliers')
        assert response.status_code == 200

    def test_get_briefs(self):
        response = self.client.get('/dashboard/briefs')
        assert response.status_code == 200

    def test_get_roles(self):
        response = self.client.get('/dashboard/roles')
        assert response.status_code == 200

        data = json.loads(response.get_data())

        # Check if 'junior' and 'senior' have been stripped from the name
        for role in data['roles']['top_roles']:
            assert 'junior' not in role['name'].lower()
            assert 'senior' not in role['name'].lower()
