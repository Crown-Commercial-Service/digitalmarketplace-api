from flask import redirect
from app.api import api
from app.api.helpers import (
    not_found
)
from app.api.services import key_values_service


@api.route('/r/<string:key>', methods=['GET'])
def get_redirect(key):
    """Get redirect
    ---
    tags:
      - redirects
    parameters:
      - name: key
        in: path
        type: string
        required: true
    responses:
      302:
        description: a redirect
    """

    key_value = key_values_service.get_by_key('redirects')
    redirect_url = key_value.get('data', {}).get(key)
    if not redirect_url:
        not_found('redirect not found')

    return redirect(redirect_url)
