import pendulum

from app.api.business.agreement_business import get_old_agreements
from tests.app.helpers import BaseApplicationTest


class TestOldAgreement(BaseApplicationTest):
    def setup(self):
        super(TestOldAgreement, self).setup()

    def test_old_agreement_end_dates_are_in_the_past(self, master_agreements):
        old_agreements = get_old_agreements()
        now = pendulum.now('utc')

        assert len(old_agreements) == 2
        for agreement in old_agreements:
            assert agreement.end_date < now
