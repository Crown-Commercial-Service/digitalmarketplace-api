from flask import jsonify
from flask_login import login_required, current_user
from app.api import api
from app.api.services import briefs, suppliers
from app.api.helpers import role_required


@api.route('/seller-dashboard', methods=['GET'])
@login_required
@role_required('supplier')
def seller_dashboard():
    """Seller dashboard (role=supplier)
    ---
    tags:
      - dashboard
    definitions:
      SellerDashboardItems:
        type: object
        properties:
            items:
              type: array
              items:
                $ref: '#/definitions/SellerDashboardItem'
            supplier:
              type: object
              properties:
                code:
                  type: string
                name:
                  type: string
      SellerDashboardItem:
        type: object
        properties:
          id:
            type: integer
          name:
            type: string
          closed_at:
            type: string
          status:
            type: string
    responses:
      200:
        description: Supplier dashboard info
        schema:
          $ref: '#/definitions/SellerDashboardItems'

    """
    supplier = suppliers.first(code=current_user.supplier_code)
    supplier_responses = briefs.get_supplier_responses(current_user.supplier_code)

    return jsonify(items=supplier_responses, supplier={'name': supplier.name, 'code': supplier.code}), 200
