from flask import jsonify
from flask_login import current_user, login_required
from app.auth import auth
from app.utils import get_json_from_request, json_has_required_keys
from app.auth.suppliers import get_supplier, update_supplier_details, valid_supplier


@auth.route('/supplier', methods=['GET'])
@login_required
def get_supplier_profile():
    if not valid_supplier(current_user):
        return jsonify(message="Only users with role supplier can access supplier details"), 401
    else:
        supplier = get_supplier(current_user.supplier_code)
        return jsonify(user=supplier), 200


@auth.route('/supplier', methods=['POST', 'PATCH'])
@login_required
def update_supplier_profile():
    if not valid_supplier(current_user):
        return jsonify(message="Only users with role supplier can update supplier details"), 401

    try:
        json_payload = get_json_from_request()
        updated_supplier = update_supplier_details(current_user.supplier_code, **json_payload)
        return jsonify(user=updated_supplier), 200

    except Exception as error:
        return jsonify(message=error.message), 400
