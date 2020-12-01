import pytest

from app.supplier_utils import is_g12_recovery_supplier
from tests.bases import BaseApplicationTest


class TestG12RecoverySupplier(BaseApplicationTest):
    @pytest.mark.parametrize(
        'g12_recovery_supplier_ids, expected_result',
        [
            (None, False),
            ('', False),
            (42, False),
            ('12:32', False),
            ([123456, 789012], False),
            ('123456', True),
            ('123456,789012', True),
        ]
    )
    def test_returns_expected_value_for_input(self, g12_recovery_supplier_ids, expected_result):
        self.app.config['DM_G12_RECOVERY_SUPPLIER_IDS'] = g12_recovery_supplier_ids
        assert is_g12_recovery_supplier(123456) is expected_result
