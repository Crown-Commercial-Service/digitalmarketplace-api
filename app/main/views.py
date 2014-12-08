from . import main
from flask import abort
from flask import make_response
from flask import render_template
from flask import request

from app import services
from app.services import g6importService


@main.route('/')
def index():
    return render_template('main.html')


# Test this locally by running the command:
# curl -i -H "Content-Type: application/json" \
# -X POST \
# -d @example_listings/scs-listing.json \
# 127.0.0.1:5000/g6/service/add
@main.route('/g6/service/add', methods=['POST'])
def addSCS():
    if not request.json:
        abort(400)
    if services.g6importService.validate_json(request.json):
        return "JSON Uploaded OK"
    else:
        return make_response("JSON was not a valid format", 422)
