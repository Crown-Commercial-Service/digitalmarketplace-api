from flask import current_app, abort, request


def get_api_key_from_request(request):
    key = None
    if request and request.headers.get(current_app.config['DM_API_KEY_HEADER'], None):
        key = request.headers.get(current_app.config['DM_API_KEY_HEADER'], None)
    return key


def requires_authentication():
    if current_app.config['AUTH_REQUIRED']:
        incoming_token = get_token_from_headers(request.headers)

        if not incoming_token:
            abort(401, "Unauthorized; bearer token must be provided")
        if not token_is_valid(incoming_token):
            abort(403, "Forbidden; invalid bearer token provided {}".format(incoming_token))


def token_is_valid(incoming_token):
    return incoming_token in get_allowed_tokens_from_config(current_app.config)


def get_allowed_tokens_from_config(config):
    """Return a list of allowed auth tokens from the application config"""
    return [token for token in config.get('DM_API_AUTH_TOKENS', '').split(':') if token]


def get_token_from_headers(headers):
    auth_header = headers.get('Authorization', '')
    if auth_header[:7] != 'Bearer ':
        return None
    return auth_header[7:]
