from flask import jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError

from . import status
from . import utils
from dmutils.status import get_version_label, get_flags


@status.route('/_status')
def status_no_db():

    try:
        return jsonify(
            status="ok",
            version=get_version_label(),
            db_version=utils.get_db_version(),
            flags=get_flags(current_app)
        )

    except SQLAlchemyError:
        current_app.logger.exception('Error connecting to database')
        return jsonify(
            status="error",
            version=get_version_label(),
            message="Error connecting to database",
            flags=get_flags(current_app)
        ), 500
