import pendulum

from app.api.business.validators import SupplierValidator
from app.api.services import (application_service, key_values_service,
                              master_agreement_service, suppliers)
from app.models import MasterAgreement


def get_old_agreements():
    now = pendulum.now('utc')
    return master_agreement_service.filter(
        MasterAgreement.end_date < now
    ).all()


def get_current_agreement():
    now = pendulum.now('utc')
    return master_agreement_service.filter(
        MasterAgreement.start_date <= now,
        MasterAgreement.end_date >= now
    ).one_or_none()


def get_new_agreement():
    now = pendulum.now('utc')
    return master_agreement_service.filter(
        MasterAgreement.start_date > now
    ).one_or_none()


def has_signed_current_agreement(supplier):
    current_agreement = get_current_agreement()

    if current_agreement:
        old_agreements = get_old_agreements()
        old_agreement_ids = [agreement.id for agreement in old_agreements]

        if current_agreement.id in old_agreement_ids:
            to_check = old_agreement_ids
        else:
            to_check = [current_agreement.id]

        signed = next(
            iter([
                sa
                for sa in supplier.signed_agreements
                if sa.agreement_id in to_check
            ]),
            None
        )

        if signed:
            return True

    return False


def use_old_work_order_creator(published_at):
    if not published_at:
        return False

    current_agreement = get_current_agreement()
    old_work_order_creator = True

    if current_agreement:
        old_agreements = get_old_agreements()
        old_agreement_ids = [agreement.id for agreement in old_agreements]
        if (
            current_agreement.id not in old_agreement_ids and
            published_at >= current_agreement.start_date
        ):
            old_work_order_creator = False

    return old_work_order_creator
