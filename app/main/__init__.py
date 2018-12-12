from flask import Blueprint

from ..authentication import requires_authentication

main = Blueprint('main', __name__)

main.before_request(requires_authentication)


@main.after_request
def add_cache_control(response):
    response.cache_control.max_age = 24 * 60 * 60
    return response


from .views import (
    agreements,
    audits,
    brief_responses,
    briefs,
    buyer_domains,
    direct_award,
    drafts,
    frameworks,
    outcomes,
    services,
    suppliers,
    users,
)
