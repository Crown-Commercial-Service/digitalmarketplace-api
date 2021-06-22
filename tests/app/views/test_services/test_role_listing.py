from flask import json
from nose.tools import assert_in, assert_equal, assert_is_not_none
from tests.app.helpers import BaseApplicationTest


class TestRoleListing(BaseApplicationTest):
    def test_listing(self):
        response = self.client.get('/roles')
        data = json.loads(response.get_data())
        assert_in('roles', data)
        roles = data['roles']
        assert len(roles) > 0
        for role in roles:
            assert_equal(set(role.keys()), {'role', 'category', 'roleAbbreviation', 'categoryAbbreviation'})
            assert_is_not_none(role['role'])
            assert_is_not_none(role['category'])
            assert_is_not_none(role['roleAbbreviation'])
            assert_is_not_none(role['categoryAbbreviation'])
