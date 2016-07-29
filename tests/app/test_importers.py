import csv

from app import create_app, db
from app.models import Supplier
from helpers import BaseApplicationTest
from nose.tools import assert_equal, assert_greater, assert_in, assert_is_not_none, assert_true, assert_is

from scripts.importers import import_prices, import_suppliers


class TestImporters(BaseApplicationTest):

    supplier_data_file_name = 'example_listings/test_source_data/DMP Data Source - Test data.csv'
    price_data_file_name = 'example_listings/test_source_data/DMP Data Source - Test price data.csv'

    def _import_suppliers(self):
        with open(self.supplier_data_file_name) as data_file:
            num_failures, num_successes = import_suppliers.run_import(data_file, self.client)
        return num_failures, num_successes

    def test_supplier_importer(self):
        with self.app.app_context():
            with open(self.supplier_data_file_name) as data_file:
                num_entries = sum(1 for r in csv.DictReader(data_file) if r['Ready to upload'] == 'Y')
                assert_greater(num_entries, 0)
            num_failures, num_successes = self._import_suppliers()
            assert_equal(num_failures, 0)
            assert_equal(num_successes, num_entries)

            alpha = Supplier.query.filter_by(code='001').first()
            assert_is_not_none(alpha)
            assert_in('Alpha', alpha.name)

    def _import_prices(self):
        with open(self.price_data_file_name, 'r') as data_file:
            num_failures, num_successes = import_prices.run_import(data_file, self.client)
        return num_failures, num_successes

    def test_supplier_prices(self):
        with self.app.app_context():
            num_failures, num_good_suppliers = self._import_suppliers()
            assert_equal(num_failures, 0)
            assert_greater(num_good_suppliers, 0)

            num_failures, num_successes = self._import_prices()
            assert_equal(num_failures, 0)
            assert_equal(num_successes, num_good_suppliers)

            alpha = Supplier.query.filter_by(code='001').first()
            assert_is_not_none(alpha)
            assert_greater(len(alpha.prices), 0)
