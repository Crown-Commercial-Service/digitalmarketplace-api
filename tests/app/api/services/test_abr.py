import pytest

from app.api.services import abr_service
from tests.app.helpers import BaseApplicationTest


class TestAbrService(BaseApplicationTest):
        def setup(self):
            super(TestAbrService, self).setup()
        
        # @pytest.fixture()

        def test_get_business_info_by_abn(self, email_address, abn):
            test = abr_service.get_business_info_by_abn(email_address, abn)


