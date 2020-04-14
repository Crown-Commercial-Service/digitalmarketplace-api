from app.api.business.validators.brief_specialist_validator import whitelist_fields as whitelist_fields_specialist
from app.api.business.validators.brief_atm_validator import whitelist_fields as whitelist_fields_atm
from app.api.business.validators.brief_training_validator import whitelist_fields as whitelist_fields_training
from app.api.business.validators.brief_validator import whitelist_fields as whitelist_fields_rfx


def is_open_to_all(brief):
    if brief.lot.slug == 'atm' or (
        brief.lot.slug == 'specialist' and brief.data.get('openTo') == 'all'
    ):
        return True

    return False


def remove_keys_not_whitelisted(brief):
    field_whitelists = {
        'atm': whitelist_fields_atm,
        'rfx': whitelist_fields_rfx,
        'specialist': whitelist_fields_specialist,
        'training2': whitelist_fields_training
    }
    for actual_key in brief.data.keys():
        whitelisted_keys = [key['name'] for key in field_whitelists[brief.lot.slug]]
        if actual_key not in whitelisted_keys:
            del brief.data[actual_key]
    return brief
