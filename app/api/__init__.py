import rollbar
from dmutils.csrf import check_valid_csrf
from dmutils.user import User as LoginUser
from sqlalchemy.orm import noload
from flask import Blueprint, request, current_app
from flask_login import LoginManager
from app.models import User
from app.api.business import supplier_business, team_business
from app.api.services import api_key_service
from base64 import b64decode
from app import encryption
from app.api.helpers import abort
from app.authentication import get_api_key_from_request

api = Blueprint('api', __name__)
login_manager = LoginManager()


@api.record_once
def on_load(state):
    login_manager.init_app(state.app)


@login_manager.user_loader
def load_user(userid):
    user = User.query.options(
        noload('*')
    ).get(int(userid))

    if user is not None:
        notification_count = get_notification_count(user)
        teams = get_teams(user)
        user = LoginUser(user.id, user.email_address, user.supplier_code, None, user.locked,
                         user.active, user.name, user.role, user.terms_accepted_at, user.application_id,
                         user.frameworks, notification_count, teams, user.agency_id)

    return user


def get_notification_count(user):
    notification_count = None
    if user.role == 'supplier':
        errors_warnings = supplier_business.get_supplier_messages(user.supplier_code, False)
        notification_count = len(errors_warnings.errors + errors_warnings.warnings)

    return notification_count


def get_teams(user):
    if user.role == 'buyer':
        return team_business.get_user_teams(user.id)
    return None


@api.before_request
def check_csrf_token():
    if request.method in ('POST', 'PATCH', 'PUT', 'DELETE'):
        '''
        Only check CSRF tokens if there is no valid API key in the request. The API key comes via a header which will
        not be forwarded by browsers automatically in authenticated requests, so the presence of a valid API key in the
        request proves authenticity like a CSRF token.
        '''
        api_key = get_api_key_from_request(request)
        if not api_key or not api_key_service.get_key(api_key):
            new_csrf_valid = check_valid_csrf()

            if not (new_csrf_valid):
                rollbar.report_message('csrf.invalid_token: Aborting request check_csrf_token()', 'error', request)
                abort('Invalid CSRF token. Please try again.')


@api.after_request
def add_cache_control(response):
    response.headers['Cache-control'] = 'no-cache, no-store'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = 0
    return response


@login_manager.request_loader
def load_user_from_request(request):
    if not current_app.config.get('BASIC_AUTH'):
        return None

    payload = get_token_from_headers(request.headers)

    if payload is None:
        return None

    email_address, password = b64decode(payload).split(':', 1)
    user = User.get_by_email_address(email_address.lower())

    if user is not None:
        if encryption.authenticate_user(password, user):
            notification_count = get_notification_count(user)
            user = LoginUser(user.id, user.email_address, user.supplier_code, None, user.locked,
                             user.active, user.name, user.role, user.terms_accepted_at, user.application_id,
                             user.frameworks, notification_count, user.agency_id)
            return user


from app.api.views import (briefs,  # noqa
                           brief_responses,
                           buyer_dashboard,
                           download_reports,
                           users,
                           feedback,
                           messages,
                           suppliers,
                           seller_dashboard,
                           seller_edit,
                           tasks,
                           opportunities,
                           questions,
                           key_values,
                           insight,
                           teams,
                           domains,
                           evidence,
                           redirects)

from app.api.views.reports import (  # noqa
    brief,
    brief_response,
    suppliers
)

from app.api.business.validators import (  # noqa
    application_validator,
    supplier_validator
)


def get_token_from_headers(headers):
    print headers
    auth_header = headers.get('Authorization', '')
    if auth_header[:6] != 'Basic ':
        return None
    return auth_header[6:]
