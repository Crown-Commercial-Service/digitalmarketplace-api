from flask import current_app, jsonify
from flask_login import login_required
from app.api import api
from app.api.helpers import role_required
from app.api.services.reports import suppliers_service
from itertools import groupby


@api.route('/reports/supplier/unassessed', methods=['GET'])
@login_required
@role_required('admin')
def get_unassessed():
    """Unassessed Suppliers
    ---
    tags:
      - reports
    definitions:
      UnassessedSuppliers:
        type: object
        properties:
          case_study_urls:
            type: array
          domain_id:
            type: integer
          domain_name:
            type: string
          supplier_code:
            type: integer
          supplier_id:
            type: integer
          supplier_last_logged_in:
            type: string
          supplier_name:
            type: integer
          supplier_price:
            type: string
    responses:
      200:
        description: Unassessed Suppliers
        schema:
          $ref: '#/definitions/UnassessedSuppliers'

    """
    unassessed = suppliers_service.get_unassessed()
    result = []
    frontend_address = current_app.config['FRONTEND_ADDRESS']
    i = None
    case_study_urls = []
    for key, group in groupby(unassessed, lambda s: s['supplier_code']):
        case_study_urls = []
        i = None
        for g in group:
            if i is None:
                i = g
            case_study_urls.append('{}/case-study/{}'.format(frontend_address, g['case_study_id']))

        i['case_study_urls'] = case_study_urls
        del i['case_study_id']
        result.append(i)

    return jsonify(result)


@api.route('/reports/supplier/all', methods=['GET'])
@login_required
@role_required('admin')
def get_all_suppliers():
    """All Suppliers
    ---
    tags:
      - reports
    definitions:
      Suppliers:
        type: object
        properties:
          code:
            type: number
          name:
            type: string
          abn:
            type: string
          status:
            type: string
          creation_time:
            type: string
          sme:
            type: boolean
          categories:
            type: array
    responses:
      200:
        description: All Suppliers
        schema:
          $ref: '#/definitions/Suppliers'

    """
    result = suppliers_service.get_suppliers()
    return jsonify({
        'items': result,
        'total': len(result)
    })
