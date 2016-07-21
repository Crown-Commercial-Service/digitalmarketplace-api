from flask import Blueprint

# These modules depend on explorer already being set up.  PEP8 rule disabled.
# FIXME: refactor out circular import
explorer = Blueprint('explorer', __name__)  # noqa

from . import views
