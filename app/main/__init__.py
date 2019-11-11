from flask import Blueprint

from ..authentication import requires_authentication

main = Blueprint('main', __name__)

main.before_request(requires_authentication)


@main.after_request
def add_cache_control(response):
    response.cache_control.max_age = 24 * 60 * 60
    return response


# These modules depend on main already being set up.  PEP8 rule disabled.
# FIXME: refactor out circular import
from .views import suppliers, services, users, drafts, audits, frameworks, briefs, \
    brief_responses, work_orders, case_studies, metrics, applications, assessments, projects, \
    evidence, teams, agencies  # noqa
from . import errors  # noqa
