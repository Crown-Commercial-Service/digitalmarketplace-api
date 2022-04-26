import pendulum
from app.api.business.brief.brief_business import get_lockout_dates


def validate_closed_at_lockout(date):
    if not date:
        return False
    parsed = pendulum.parse(date).in_timezone('Australia/Canberra').start_of('day')
    lockout_dates = get_lockout_dates()
    if lockout_dates['startDate'] and lockout_dates['endDate']:
        if parsed.date() >= lockout_dates['startDate'] and parsed.date() <= lockout_dates['endDate']:
            return False
    return True
