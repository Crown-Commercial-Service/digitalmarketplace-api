from flask import render_template, jsonify

from . import main
from ..lib.authentication import requires_authentication
from ..models import Service


@main.route('/')
@requires_authentication
def index():
    return render_template('main.html')


@main.route('/services/<id>')
def get_service(id):
    service = Service.query.filter(Service.id == id).first_or_404()

    return jsonify(id=id, data=service.data)
