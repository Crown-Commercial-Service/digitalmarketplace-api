from flask import jsonify

from . import status
from .. import utils


@status.route('/_status')
def status_no_db():
    return jsonify(status="ok", version=utils.get_version_label())
