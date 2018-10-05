from flask import jsonify
from flask_login import login_required
from app.api import api
from app.api.helpers import (
    abort,
    role_required
)
from app.api.services import (key_values_service)
from app.utils import get_json_from_request


@api.route('/keyvalue/<string:key>', methods=['GET'])
@login_required
@role_required('admin')
def get_key_value(key):
    """Get key value (role=admin)
    ---
    tags:
      - key_value
    security:
      - basicAuth: []
    parameters:
      - name: key
        in: path
        type: string
        required: true
    definitions:
      KeyValue:
        properties:
          id:
            type: integer
          key:
            type: string
          data:
            type: object
          last_update_time:
            type: string
    responses:
      200:
        description: A key value
        schema:
          $ref: '#/definitions/KeyValue'
    """
    key_value = key_values_service.get_by_key(key)
    return jsonify(key_value), 200


@api.route('/keyvalue/<string:key>', methods=['POST'])
@login_required
@role_required('admin')
def upsert(key):
    """Upsert a key value (role=admin)
    ---
    tags:
      - key_value
    security:
      - basicAuth: []
    parameters:
      - name: key
        in: path
        type: string
        required: true
      - name: data
        in: body
        required: true
        schema:
          $ref: '#/definitions/KeyValueUpsert'
    definitions:
          KeyValueUpsert:
            properties:
              data:
                type: object
    responses:
      200:
        description: A key value
        type: object
        schema:
          $ref: '#/definitions/KeyValue'
    """
    try:
        json_payload = get_json_from_request()
        data = json_payload.get('data')
        saved = key_values_service.upsert(key, data)
        return jsonify(saved), 200

    except Exception as error:
        return abort(error.message)
