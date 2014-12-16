from functools import wraps

from flask import current_app, abort, request


def requires_authentication(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if current_app.config['AUTH_REQUIRED']:
            incoming_token = get_token_from_headers(request.headers)
            tokens_path = current_app.config['AUTH_TOKENS_PATH']

            if not incoming_token:
                abort(401)
            if not token_is_valid(tokens_path, incoming_token):
                abort(403)

        return view(*args, **kwargs)

    return wrapped_view


def token_is_valid(token_path, incoming_token):
    return incoming_token in get_allowed_tokens(token_path)


def get_allowed_tokens(token_path):
    with open(token_path) as f:
        return [token.strip() for token in f.readlines()]


def get_token_from_headers(headers):
    auth_header = headers.get('Authorization', '')
    if auth_header[:7] != 'Bearer ':
        return None
    return auth_header[7:]
