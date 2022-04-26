import pendulum
from flask import current_app
from app.api.business.validators import SupplierValidator
from app.api.business.brief.user_status import BriefUserStatus
from app.api.services import suppliers, briefs, domain_service, brief_responses_service, key_values_service
from app.datetime_utils import combine_date_and_time, parse_time_of_day


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
        if brief.lot.slug != 'specialist' and not user_status.is_assessed_for_category():
            return False, 'Supplier is not assessed for the category of the opportunity'

    if not user_status.is_invited():
        return False, 'Supplier is not selected to respond or does not meet the minimum requirements to respond'

    if check_response_limit and user_status.has_responded(submitted_only=False):
        return False, 'Supplier has reached the permitted amount of draft/submitted responses for this opportunity'

    return True, ''


def remove_keys_not_whitelisted(brief):
    from app.api.business.validators.brief_specialist_validator import whitelist_fields as whitelist_fields_specialist
    from app.api.business.validators.brief_atm_validator import whitelist_fields as whitelist_fields_atm
    from app.api.business.validators.brief_training_validator import whitelist_fields as whitelist_fields_training
    from app.api.business.validators.brief_validator import whitelist_fields as whitelist_fields_rfx
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


def get_lockout_dates(formatted=False):
    lockout_period = {
        'startDate': None,
        'endDate': None
    }
    lockout_date_start = None
    lockout_date_end = None
    lockout_dates = key_values_service.get_by_key('lockout_dates')
    if lockout_dates:
        try:
            lockout_date_start = (
                pendulum.parse(lockout_dates['data']['startDate'], tz='Australia/Canberra').date()
            )
            lockout_date_end = (
                pendulum.parse(lockout_dates['data']['endDate'], tz='Australia/Canberra').date()
            )
        except pendulum.parsing.exceptions.ParserError:
            lockout_date_start = None
            lockout_date_end = None
    if lockout_date_start and lockout_date_end:
        lockout_period['startDate'] = lockout_date_start.strftime('%Y-%m-%d') if formatted else lockout_date_start
        lockout_period['endDate'] = lockout_date_end.strftime('%Y-%m-%d') if formatted else lockout_date_end
    return lockout_period


def get_lockout_question_close_date(questions_closed_at, closed_at, lockout_period=None):
    if lockout_period:
        DEADLINES_TZ_NAME = current_app.config['DEADLINES_TZ_NAME']
        DEADLINES_TIME_OF_DAY = current_app.config['DEADLINES_TIME_OF_DAY']
        t = parse_time_of_day(DEADLINES_TIME_OF_DAY)
        if closed_at == lockout_period['endDate'].add(days=1):
            questions_closed_at = combine_date_and_time(
                lockout_period['startDate'].add(days=-1), t, DEADLINES_TZ_NAME).in_tz('UTC')
        elif closed_at >= lockout_period['endDate'] and closed_at <= lockout_period['endDate'].add(days=3):
            questions_closed_at = combine_date_and_time(
                lockout_period['endDate'].add(days=1), t, DEADLINES_TZ_NAME).in_tz('UTC')
    return questions_closed_at
