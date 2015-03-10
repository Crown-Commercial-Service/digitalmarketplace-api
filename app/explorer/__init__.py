from flask import Blueprint

explorer = Blueprint('explorer', __name__)

from . import views
