from flask import render_template
from ..lib.authentication import requires_authentication
from . import main


@main.route('/')
@requires_authentication
def index():
    return render_template('main.html')
