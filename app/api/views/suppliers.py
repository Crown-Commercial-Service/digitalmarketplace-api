from flask import jsonify, request
from flask_login import login_required
from app.api import api
from app.utils import get_json_from_request
from app.api.suppliers import get_supplier
from app.api.helpers import role_required, is_current_supplier
from app.api.services import suppliers, domain_service


@api.route('/suppliers/<int:code>', methods=['GET'], endpoint='get_supplier')
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
        schema:
          $ref: '#/definitions/Supplier'
    """
    return get_supplier(code)


@api.route('/suppliers/search', methods=['GET'])
def get_suppliers():
    """Suppliers search names by keyword
    ---
    tags:
        - suppliers
    definitions:
        SupplierMinimal:
            type: object
            properties:
                name:
                    type: string
                code:
                    type: integer
                panel:
                    type: boolean
                sme:
                    type: boolean
        Suppliers:
            type: object
            properties:
                sellers:
                    type: array
                    items:
                        $ref: '#/definitions/SupplierMinimal'
    parameters:
        - name: keyword
          in: query
          type: string
          required: true
          description: the keyword to search on
        - name: category
          in: query
          type: string
          required: false
          description: the seller category to filter on
    responses:
        200:
            description: a list of matching suppliers
            schema:
                $ref: '#/definitions/Suppliers'
        400:
            description: invalid request data, such as a missing keyword param
    """
    keyword = request.args.get('keyword') or ''
    category = request.args.get('category') or ''
    if keyword:
        results = suppliers.get_suppliers_by_name_keyword(keyword,
                                                          framework_slug='digital-marketplace',
                                                          category=category)
        supplier_results = []
        for result in results:
            if len(result.assessed_domains) > 0:
                if category:
                    domain = domain_service.get_by_name_or_id(int(category))
                    if not domain or domain.name not in result.assessed_domains:
                        continue
                supplier = {}
                supplier['name'] = result.name
                supplier['code'] = result.code
                supplier_results.append(supplier)

        return jsonify(sellers=supplier_results), 200
    else:
        return jsonify(message='You must provide a keyword param.'), 400
