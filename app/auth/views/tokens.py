from flask import jsonify
from app.auth.helpers import decode_creation_token
from app.auth import auth
from dmutils.email import InvalidToken


def decode_token(token):
    try:
        data = decode_creation_token(token.encode())
        return jsonify(data)

    except InvalidToken:
        return jsonify(message='The token provided is invalid. It may have expired'), 400

    except TypeError:
        return jsonify(
            message='The invite token passed to the server is not a recognizable token format'
        ), 400


@auth.route('/tokens/<string:token>', methods=['GET'], endpoint='get_token')
def get(token):
    """Decode token
    ---
    tags:
      - tokens
    consumes:
      - application/json
    parameters:
      - name: token
        in: path
        type: string
        required: true
        default: all
    responses:
      200:
        description: User
        type: object
        properties:
          email_address:
            type: string
          name:
            type: string
          user_type:
            type: string
          framework:
            type: string
    """
    return decode_token(token)


# deprecated
@auth.route('/signup/validate-invite/<string:token>', methods=['GET'])
def get_deprecated(token):
    return decode_token(token)
