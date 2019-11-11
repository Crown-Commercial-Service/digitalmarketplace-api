import pendulum

from app.api.business.agreement_business import (get_current_agreement,
                                                 get_old_agreements,
                                                 has_signed_current_agreement)
from app.models import SignedAgreement
from tests.app.helpers import BaseApplicationTest


class TestHasSignedAgreement(BaseApplicationTest):
    def setup(self):
        super(TestHasSignedAgreement, self).setup()

    def test_seller_has_signed_current_agreement_with_old_signed_agreements(self, master_agreements, supplier, user):
        old_agreements = get_old_agreements()
        current_agreement = get_current_agreement()
        past_and_present_agreements = [agreement for agreement in old_agreements]
        past_and_present_agreements.append(current_agreement)

        supplier.signed_agreements = [
            SignedAgreement(
                agreement_id=agreement.id,
                user_id=1,
                signed_at=agreement.start_date.add(days=2)
            )
            for agreement in past_and_present_agreements
        ]

        signed_current_agreement = has_signed_current_agreement(supplier)

        assert signed_current_agreement is True

    def test_seller_has_signed_current_agreement_without_old_signed_agreements(self, master_agreements, supplier, user):
        current_agreement = get_current_agreement()

        supplier.signed_agreements = [
            SignedAgreement(
                agreement_id=current_agreement.id,
                user_id=1,
                signed_at=current_agreement.start_date.add(days=2)
            )
        ]

        signed_current_agreement = has_signed_current_agreement(supplier)

        assert signed_current_agreement is True

    def test_seller_has_not_signed_current_agreement_with_old_signed_agreements(self, master_agreements,
                                                                                supplier, user):
        old_agreements = get_old_agreements()

        supplier.signed_agreements = [
            SignedAgreement(
                agreement_id=agreement.id,
                user_id=1,
                signed_at=agreement.start_date.add(days=2)
            )
            for agreement in old_agreements
        ]

        signed_current_agreement = has_signed_current_agreement(supplier)

        assert signed_current_agreement is False

    def test_seller_has_not_signed_current_agreement_without_any_signed_agreements(self, master_agreements,
                                                                                   supplier, user):
        signed_current_agreement = has_signed_current_agreement(supplier)

        assert signed_current_agreement is False
