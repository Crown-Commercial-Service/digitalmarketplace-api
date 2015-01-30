from flask import jsonify

from . import status


@status.route('/_status')
def status_no_db():
    return jsonify(status="ok")
