import pendulum

from app.api.business.agreement_business import get_new_agreement
from tests.app.helpers import BaseApplicationTest


class TestNewAgreement(BaseApplicationTest):
    def setup(self):
        super(TestNewAgreement, self).setup()

    def test_new_agreement_start_date_is_in_the_future(self, master_agreements):
        new_agreement = get_new_agreement()
        now = pendulum.now('utc')

        assert new_agreement.start_date > now
