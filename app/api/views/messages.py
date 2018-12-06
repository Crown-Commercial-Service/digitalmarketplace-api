from flask import jsonify, request
from flask_login import login_required
from app.api import api
from app.api.helpers import role_required, is_current_supplier
from app.api.business import supplier_business


@api.route('/supplier/<int:code>/messages', methods=['GET'])
@login_required
@role_required('supplier')
@is_current_supplier
def get_supplier_messages(code):
    """Get supplier messages (role=supplier)
    ---
    tags:
      - messages
    security:
      - basicAuth: []
    parameters:
      - name: code
        in: path
        type: int
        required: true
    definitions:
      Message:
        type: object
        properties:
          severity:
            type: string
          message:
            type: string
          step:
            type: string
      Messages:
        properties:
          warnings:
            type: array
            items:
              $ref: '#/definitions/Message'
          errors:
            type: array
            items:
              $ref: '#/definitions/Message'
    responses:
      200:
        description: supplier messages
        schema:
          $ref: '#/definitions/Messages'
    """
    skip_application_check = request.args.get('skip_application_check', True)
    messages = supplier_business.get_supplier_messages(code, skip_application_check)
    if messages:
        return jsonify(warnings=messages.warnings, errors=messages.errors), 200
    else:
        return jsonify(warnings=[], errors=[]), 200
