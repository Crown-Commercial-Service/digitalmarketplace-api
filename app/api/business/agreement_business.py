import pendulum
from app.api.business.validators import SupplierValidator
from app.api.services import (
    suppliers,
    application_service,
    agreement_service,
    key_values_service
)


def get_current_agreement():
    key_value = key_values_service.get_by_key('current_master_agreement')

    agreement = None
    if key_value:
        now = pendulum.now('Australia/Canberra').date()
        data = key_value.get('data', {})
        for k in sorted(data.keys()):
            v = data[k]
            start_date = pendulum.parse(v.get('startDate'), tz='Australia/Canberra').date()
            end_date = pendulum.parse(v.get('endDate'), tz='Australia/Canberra').date()

            if start_date <= now and end_date >= now:
                agreement = v
                agreement['agreementId'] = int(k)
                a = agreement_service.find(id=k).one_or_none()
                agreement['pdfUrl'] = a.url
                break

    return agreement


def has_signed_current_agreement(supplier):
    key_value = key_values_service.get_by_key('old_agreements')

    agreement = get_current_agreement()
    if agreement and key_value:
        old_agreements = key_value.get('data').get('oldAgreements', [])
        if agreement['agreementId'] in old_agreements:
            to_check = old_agreements
        else:
            to_check = [agreement['agreementId']]

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


def get_new_agreement():
    key_value = key_values_service.get_by_key('current_master_agreement')

    agreement = None
    if key_value:
        now = pendulum.now('Australia/Canberra').date()
        data = key_value.get('data', {})
        for k in sorted(data.keys()):
            v = data[k]
            start_date = pendulum.parse(v.get('startDate'), tz='Australia/Canberra').date()
            end_date = pendulum.parse(v.get('endDate'), tz='Australia/Canberra').date()

            if start_date > now:
                agreement = v
                agreement['agreementId'] = k
                a = agreement_service.find(id=k).one_or_none()
                agreement['pdfUrl'] = a.url
                break

    return agreement


def use_old_work_order_creator(published_at):
    if not published_at:
        return False
    key_value = key_values_service.get_by_key('old_agreements')
    agreement = get_current_agreement()
    old_work_order_creator = True
    if agreement and key_value:
        old_agreements = key_value.get('data').get('oldAgreements', [])
        if (
            agreement['agreementId'] not in old_agreements and
            published_at >= pendulum.parse(agreement.get('startDate'), tz='Australia/Canberra').date()
        ):
            old_work_order_creator = False

    return old_work_order_creator
