from functools import wraps
from flask import abort, current_app, request


def debug_only(func):
    """
    Allows a handler to be used in development and testing, without being made live.
    """
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_app.config['DEBUG']:
            abort(404)
        current_app.logger.warn('This endpoint disabled in live builds: {}'.format(request.url))
        return func(*args, **kwargs)
    return decorated_view
