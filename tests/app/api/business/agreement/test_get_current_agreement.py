import pendulum

from app.api.business.agreement_business import get_current_agreement
from tests.app.helpers import BaseApplicationTest


class TestCurrentAgreement(BaseApplicationTest):
    def setup(self):
        super(TestCurrentAgreement, self).setup()

    def test_current_agreement_is_in_the_present(self, master_agreements):
        current_agreement = get_current_agreement()
        now = pendulum.now('utc')

        assert current_agreement.start_date <= now
        assert current_agreement.end_date >= now
