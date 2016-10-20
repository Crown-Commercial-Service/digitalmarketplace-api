from nose.tools import assert_equal

from .helpers import BaseApplicationTest

from app.search_indices import delete_indices, indices_exist


class TestAdminRebuildIndex(BaseApplicationTest):

    def test_idempotent_rebuild(self):
        with self.app.app_context():
            response = self.client.post('/_admin/rebuild-index')
            assert_equal(response.status_code, 200)
            assert indices_exist()

            response = self.client.post('/_admin/rebuild-index')
            assert_equal(response.status_code, 200)
            assert indices_exist()

    def test_rebuild_after_delete(self):
        with self.app.app_context():
            delete_indices()
            assert not indices_exist()

            response = self.client.post('/_admin/rebuild-index')
            assert_equal(response.status_code, 200)
            assert indices_exist()
