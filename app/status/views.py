import os
from flask import jsonify, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from . import status
from . import utils
from dmutils.status import get_flags


@status.route('/_status')
def status_no_db():

    if 'ignore-dependencies' in request.args:
        return jsonify(
            status="ok",
        ), 200

    version = current_app.config['VERSION']

    try:
        return jsonify(
            status="ok",
            version=version,
            db_version=utils.get_db_version(),
            flags=get_flags(current_app)
        )

    except SQLAlchemyError:
        current_app.logger.exception('Error connecting to database')
        return jsonify(
            status="error",
            version=version,
            message="Error connecting to database",
            flags=get_flags(current_app)
        ), 500
