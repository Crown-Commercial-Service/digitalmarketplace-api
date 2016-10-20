from flask import Blueprint

# These modules depend on status already being set up.  PEP8 rule disabled.
# FIXME: refactor out circular import
status = Blueprint('status', __name__)  # noqa

from . import views

__all__ = ['status', 'views']
