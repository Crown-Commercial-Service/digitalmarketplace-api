import os

from flask import current_app, abort, request


def requires_authentication():
    if current_app.config['AUTH_REQUIRED']:
        incoming_token = get_token_from_headers(request.headers)

        if not incoming_token:
            abort(401)
        if not token_is_valid(incoming_token):
            abort(403, incoming_token)


def token_is_valid(incoming_token):
    return incoming_token in get_allowed_tokens_from_environment()


def get_allowed_tokens_from_environment():
    """Return a list of allowed auth tokens from the DM_AUTH_TOKENS env variable

    >>> os.environ['DM_AUTH_TOKENS'] = ''
    >>> list(get_allowed_tokens_from_environment())
    []
    >>> del os.environ['DM_AUTH_TOKENS']
    >>> list(get_allowed_tokens_from_environment())
    []
    >>> os.environ['DM_AUTH_TOKENS'] = 'ab:cd'
    >>> list(get_allowed_tokens_from_environment())
    ['ab', 'cd']
    """
    return filter(None, os.environ.get('DM_AUTH_TOKENS', '').split(":"))


def get_token_from_headers(headers):
    auth_header = headers.get('Authorization', '')
    if auth_header[:7] != 'Bearer ':
        return None
    return auth_header[7:]
