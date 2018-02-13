from flask import jsonify
from flask_login import login_required, current_user
from app.api import api
from app.api.services import assessments, briefs, suppliers
from app.api.helpers import role_required
from itertools import chain


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
    supplier_assessments = assessments.get_supplier_assessments(current_user.supplier_code)
    supplier_responses = briefs.get_supplier_responses(current_user.supplier_code)

    filtered_assessments = [a for a in supplier_assessments if not
                            any(r for r in supplier_responses if a['id'] == r['id'])]

    result = []
    for brief_response in chain(filtered_assessments, supplier_responses):
        brief_response['status'] = get_status(brief_response)
        for field in ['created_at', 'domain_name', 'domain_status']:
            brief_response.pop(field, None)
        result.append(brief_response)

    return jsonify(items=result, supplier={'name': supplier.name, 'code': supplier.code}), 200


def get_status(brief):
    if 'domain_status' in brief:
        status = {'assessed': 'Approved to apply', 'unassessed': 'Assessment requested',
                  'rejected': 'Assessment rejected'}
        return status[brief['domain_status']]

    return 'Response submitted'
