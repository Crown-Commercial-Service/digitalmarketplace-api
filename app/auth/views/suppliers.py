from flask import jsonify
from flask_login import current_user, login_required
from app.auth import auth
from app.utils import get_json_from_request
from app.auth.suppliers import get_supplier, update_supplier, get_supplier_services, get_all_suppliers
from app.auth.helpers import role_required, is_current_supplier


@auth.route('/suppliers/<int:code>', methods=['GET'], endpoint='get_supplier')
@login_required
@role_required('buyer', 'supplier')
@is_current_supplier
def get(code):
    """A supplier (role=buyer,supplier)
    ---
    tags:
      - suppliers
    security:
      - basicAuth: []
    parameters:
      - name: code
        in: path
        type: integer
        required: true
        default: all
    definitions:
      SupplierService:
        type: object
        properties:
          id:
            type: integer
          name:
            type: string
          subCategories:
            type: array
            items:
              $ref: '#/definitions/SupplierCategory'
      SupplierCategory:
        type: object
        properties:
          id:
            type: integer
          name:
            type: string
      Supplier:
        type: object
        properties:
          abn:
            type: string
          address_address_line:
            type: string
          address_country:
            type: string
          address_postal_code:
            type: string
          address_state:
            type: string
          address_suburb:
            type: string
          category_name:
            type: string
          code:
            type: string
          contact_email:
            type: string
          contact_name:
            type: string
          contact_phone:
            type: string
          email:
            type: string
          id:
            type: number
          linkedin:
            type: string
          name:
            type: string
          phone:
            type: string
          regions:
            type: array
            items:
                type: object
                properties:
                  name:
                    type: string
                  state:
                    type: string
          representative:
            type: string
          services:
            type: array
            items:
                $ref: '#/definitions/SupplierService'
          summary:
            type: string
          website:
            type: string
    responses:
      200:
        description: A supplier
        type: object
        properties:
          supplier:
              $ref: '#/definitions/Supplier'
    """
    return get_supplier(code)


@auth.route('/suppliers/<int:code>', methods=['POST'], endpoint='update_supplier')
@login_required
@role_required('buyer', 'supplier')
@is_current_supplier
def update(code):
    """Update a supplier (role=buyer,supplier)
    ---
    tags:
      - suppliers
    security:
      - basicAuth: []
    parameters:
      - name: code
        in: path
        type: integer
        required: true
        default: all
    responses:
      200:
        description: A supplier
        type: object
        properties:
          supplier:
              $ref: '#/definitions/Supplier'
    """
    try:
        json_payload = get_json_from_request()
        supplier = update_supplier(code, **json_payload)

        return jsonify(supplier=supplier.serializable), 200

    except Exception as error:
        return jsonify(message=error.message), 400


@auth.route('/suppliers', methods=['GET'], endpoint='get_all_suppliers')
@login_required
@role_required('buyer')
def get_all():
    """All suppliers grouped by category (role=buyer)
    ---
    tags:
      - suppliers
    security:
      - basicAuth: []
    responses:
      200:
        description: A supplier
        type: object
        properties:
          categories:
            type: array
            items:
              type: object
              properties:
                name:
                  type: string
                suppliers:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: integer
                      name:
                        type: string
    """
    return get_all_suppliers()


# deprecated routes
@auth.route('/supplier', methods=['GET'])
@login_required
@role_required('supplier')
def get_deprecated():
    return get_supplier(current_user.supplier_code)


@auth.route('/supplier/<int:code>', methods=['GET'])
@login_required
@role_required('buyer', 'supplier')
def get_by_code_deprecated(code):
    return get_supplier(code)


@auth.route('/supplier/services', methods=['GET'])
@login_required
@role_required('supplier')
def get_services_deprecated():
    return get_supplier_services(current_user.supplier_code)


@auth.route('/supplier', methods=['POST'])
@login_required
@role_required('supplier')
def update_deprecated():
    try:
        json_payload = get_json_from_request()
        supplier = update_supplier(current_user.supplier_code, **json_payload)

        return jsonify(user=supplier.serializable), 200

    except Exception as error:
        return jsonify(message=error.message), 400
