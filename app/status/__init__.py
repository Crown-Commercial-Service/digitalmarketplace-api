from flask import Blueprint

status = Blueprint('status', __name__)

from . import views
