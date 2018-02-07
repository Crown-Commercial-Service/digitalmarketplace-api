from flask import jsonify, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from . import status
from . import utils
from ..models import Framework
from dmutils.status import get_flags
from app import search_api_client


@status.route('/_status')
def status():

    if 'ignore-dependencies' in request.args:
        return jsonify(
            status="ok",
        ), 200

    version = current_app.config['VERSION']
    apis = [
        {
            'name': 'Search API',
            'key': 'search_api_status',
            'status': search_api_client.get_status()
        },
    ]  # list for consistency with other apps - a chunk of this should move into utils?

    apis_with_errors = []

    for api in apis:
        if api['status'] is None or api['status']['status'] != "ok":
            apis_with_errors.append(api['name'])

    # if no errors found, return as is.  Else, return an error and a message
    if not apis_with_errors:
        try:
            return jsonify(
                {api['key']: api['status'] for api in apis},
                status="ok",
                frameworks={f.slug: f.status for f in Framework.query.all()},
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

    message = "Error connecting to {}.".format(
        ", ".join(apis_with_errors)
    )

    return jsonify(
        {api['key']: api['status'] for api in apis},
        status="error",
        version=version,
        message=message,
        flags=get_flags(current_app)
    ), 500
