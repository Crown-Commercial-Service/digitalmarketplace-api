from flask import jsonify, current_app
from werkzeug import exceptions

from . import main
from ..models import ValidationError


@main.app_errorhandler(ValidationError)
def validation_error(e):
    try:
        message = e.message
    except AttributeError:
        message = str(e)

    msg = 'validation error: {}'.format(message)
    current_app.logger.error(msg)
    return jsonify(error=message), 400


def generic_error_handler(e):
    # TODO: log the error
    headers = []
    error = e.description
    if e.code == 401:
        headers = [('WWW-Authenticate', 'Bearer')]
    elif e.code == 500:
        error = "Internal error"

    return jsonify(error=error), e.code, headers


def setup_generic_error_handlers():
    for k in exceptions.default_exceptions.keys():
        main.register_error_handler(k, generic_error_handler)


setup_generic_error_handlers()
