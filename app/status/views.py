from flask import jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError

from . import status
from . import utils


@status.route('/_status')
def status_no_db():

    try:
        return jsonify(status="ok", app_version=utils.get_version_label(),
                       db_version=utils.get_db_version())

    except SQLAlchemyError:
        current_app.logger.exception('Cannot connect to database.')
        return jsonify(status="error", message="Database is down"), 500
