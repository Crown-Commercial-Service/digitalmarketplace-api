from app.api.business.validators.brief_specialist_validator import whitelist_fields as whitelist_fields_specialist
from app.api.business.validators.brief_atm_validator import whitelist_fields as whitelist_fields_atm
from app.api.business.validators.brief_training_validator import whitelist_fields as whitelist_fields_training
from app.api.business.validators.brief_validator import whitelist_fields as whitelist_fields_rfx
from app.api.business.validators import SupplierValidator
from app.api.business.brief.user_status import BriefUserStatus
from app.api.services import suppliers, briefs, domain_service, brief_responses_service


def is_open_to_all(brief):
    if brief.lot.slug == 'atm' or (
        brief.lot.slug == 'specialist' and brief.data.get('openTo') == 'all'
    ):
        return True

    return False


def can_submit_response_to_brief(brief, user, check_response_limit=True):
    user_status = BriefUserStatus(brief, user)

    if user_status.has_supplier_errors() or not user_status.is_approved_seller():
        return False, 'Supplier is invalid'

    if brief.lot.slug != 'atm' or brief.data.get('openTo', '') == 'category':
        if not user_status.is_assessed_for_category():
            return False, 'Supplier is not assessed for the category of the opportunity'

    if not user_status.is_invited():
        return False, 'Supplier is not selected to respond or does not meet the minimum requirements to respond'

    if check_response_limit and user_status.has_responded(submitted_only=False):
        return False, 'Supplier has reached the permitted amount of draft/submitted responses for this opportunity'

    return True, ''


def remove_keys_not_whitelisted(brief):
    field_whitelists = {
        'atm': whitelist_fields_atm,
        'rfx': whitelist_fields_rfx,
        'specialist': whitelist_fields_specialist,
        'training2': whitelist_fields_training
    }
    for actual_key in list(brief.data.keys()):
        whitelisted_keys = [key['name'] for key in field_whitelists[brief.lot.slug]]
        if actual_key not in whitelisted_keys:
            del brief.data[actual_key]
    return brief
