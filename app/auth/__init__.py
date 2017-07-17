from flask import Blueprint
from flask_login import LoginManager
from app.models import User
from dmutils.user import User as LoginUser

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


from . import views  # noqa
