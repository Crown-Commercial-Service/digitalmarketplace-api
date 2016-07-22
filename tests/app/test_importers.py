from app import create_app, db
from app.models import Supplier
from helpers import BaseApplicationTest
from nose.tools import assert_equal, assert_in, assert_is_not_none, assert_true, assert_is

from scripts.importers import import_suppliers


class TestImporters(BaseApplicationTest):

    def test_supplier_importer(self):
        with self.app.app_context():
            with open('example_listings/test_source_data/DMP Data Source - Test data.csv', 'r') as data_file:
                num_entries = len(data_file.readlines()) - 1  # minus CSV header
                assert num_entries > 0
                data_file.seek(0)
                num_failures, num_successes = import_suppliers.run_import(data_file, self.client)
            assert_equal(num_failures, 0)
            assert_equal(num_successes, num_entries)

            alpha = Supplier.query.filter_by(code='001').first()
            assert_is_not_none(alpha)
            assert_in('Alpha', alpha.name)
