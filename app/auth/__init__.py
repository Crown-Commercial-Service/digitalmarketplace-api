import rollbar
from dmutils.csrf import check_valid_csrf
from dmutils.user import User as LoginUser
from flask import Blueprint, request, abort
from flask_login import LoginManager

from app.models import User

auth = Blueprint('auth', __name__)
login_manager = LoginManager()


@auth.record_once
def on_load(state):
    login_manager.init_app(state.app)


@login_manager.user_loader
def load_user(userid):
    user = User.query.get(int(userid))

    if user is not None:
        user = LoginUser(user.id, user.email_address, user.supplier_code, None, user.locked,
                         user.active, user.name, user.role, user.terms_accepted_at, user.application_id)
    return user


@auth.before_request
def check_csrf_token():
    if request.method in ('POST', 'PATCH', 'PUT', 'DELETE'):
        new_csrf_valid = check_valid_csrf()

        if not (new_csrf_valid):
            rollbar.report_message('csrf.invalid_token: Aborting request check_csrf_token()', 'error', request)
            abort(400, 'Invalid CSRF token. Please try again.')


from app.auth.views import briefs, users, feedback, suppliers  # noqa
