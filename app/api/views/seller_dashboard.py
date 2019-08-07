from flask import jsonify
from flask_login import login_required, current_user
from app.api import api
from app.api.services import suppliers, users, supplier_domain_service, domain_service, evidence_service, assessments
from app.api.business import supplier_business
from app.api.helpers import get_email_domain, role_required


@api.route('/supplier/dashboard', methods=['GET'])
@login_required
@role_required('supplier')
def supplier_dashboard():
    """Seller dashboard (role=supplier)
    ---
    tags:
      - dashboard
    definitions:
      SellerDashboard:
        type: object
        properties:
            supplier:
              type: object
              properties:
                code:
                  type: string
                name:
                  type: string
            messages:
              type: object
              properties:
                items:
                  $ref: '#/definitions/SellerDashboardMessageItem'
    responses:
      200:
        description: Supplier dashboard info
        schema:
          $ref: '#/definitions/SellerDashboard'

    """
    supplier = suppliers.first(code=current_user.supplier_code)
    messages = supplier_business.get_supplier_messages(current_user.supplier_code, False)
    items = messages.warnings + messages.errors

    return jsonify(
        supplier={
            'name': supplier.name,
            'code': supplier.code,
            'is_recruiter_only': True if supplier.data.get('recruiter', '') == 'yes' else False
        },
        messages={
            'items': items
        }
    ), 200


@api.route('/supplier/dashboard/messages', methods=['GET'])
@login_required
@role_required('supplier')
def get_messages():
    """Supplier dashboard (Messages) (role=supplier)
    ---
    tags:
      - dashboard
    definitions:
      SellerDashboardMessageItems:
        type: object
        properties:
            messages:
              type: array
              items:
                $ref: '#/definitions/SellerDashboardMessageItem'
      SellerDashboardMessageItem:
        type: object
        properties:
          message:
            type: string
          severity:
            type: string
    responses:
      200:
        description: Seller dashboard data for the 'Notifications' tab
        schema:
          $ref: '#/definitions/SellerDashboardMessageItems'
    """
    messages = supplier_business.get_supplier_messages(current_user.supplier_code, False)
    items = messages.warnings + messages.errors

    if messages:
        return jsonify(
            messages={
                'items': items
            }
        ), 200
    else:
        return jsonify(
            messages={
                'items': []
            }
        ), 200


@api.route('/supplier/dashboard/team', methods=['GET'])
@login_required
@role_required('supplier')
def get_team_members():
    """Supplier dashboard (Team) (role=supplier)
    ---
    tags:
      - dashboard
    definitions:
      SellerDashboardTeamItems:
        type: object
        properties:
            teams:
              type: array
              items:
                $ref: '#/definitions/SellerDashboardTeamItem'
      SellerDashboardTeamItem:
        type: object
        properties:
          email:
            type: string
          name:
            type: string
    responses:
      200:
        description: Seller dashboard data for the 'Team' tab
        schema:
          $ref: '#/definitions/SellerDashboardTeamItems'
    """
    team_members = users.get_team_members(current_user.get_id(), get_email_domain(current_user.email_address))

    return jsonify(
        teams={
            'items': team_members
        }
    ), 200


@api.route('/supplier/dashboard/categories', methods=['GET'])
@login_required
@role_required('supplier')
def get_categories():
    """Supplier dashboard (Categories) (role=supplier)
    ---
    tags:
      - dashboard
    definitions:
      SellerDashboardCategoryItems:
        type: object
        properties:
            categories:
              type: array
              items:
                $ref: '#/definitions/SellerDashboardCategoryItem'
      SellerDashboardCategoryItem:
        type: object
        properties:
          id:
            type: number
          name:
            type: string
          status:
            type: string
          is_approved:
            type: boolean
          evidence_id:
            type: number
    responses:
      200:
        description: Seller dashboard data for the 'Categories' tab
        schema:
          $ref: '#/definitions/SellerDashboardCategoryItems'
    """
    categories = []
    supplier = suppliers.get_supplier_by_code(current_user.supplier_code)
    for domain in domain_service.get_active_domains():
        is_approved = True if domain.name in supplier.assessed_domains else False
        data = {
            "id": domain.id,
            "name": domain.name,
            "previous_evidence_id": None,
            "evidence_id": None,
            "is_approved": is_approved
        }
        domain_evidence = evidence_service.get_latest_evidence_for_supplier_and_domain(
            domain.id,
            current_user.supplier_code,
        )
        if domain_evidence:
            previous_evidence = evidence_service.get_previous_submitted_evidence_for_supplier_and_domain(
                domain_evidence.id,
                domain.id,
                current_user.supplier_code
            )
            if previous_evidence and previous_evidence.status == 'rejected':
                data['previous_evidence_id'] = previous_evidence.id
            data['status'] = domain_evidence.status
            data['evidence_id'] = domain_evidence.id
        else:
            # is there a submitted case study assessment in progress?
            open_assessment = assessments.get_open_assessments(
                domain_id=domain.id,
                supplier_code=supplier.code
            )
            if open_assessment:
                data['status'] = 'submitted'
            else:
                assessed_status = suppliers.get_supplier_assessed_status(supplier.id, domain.id)
                data['status'] = assessed_status if assessed_status else 'unassessed'

        # override the status as unassessed if the domain is not in the assessed domains
        if data['status'] == 'assessed' and not is_approved:
            data['status'] = 'unassessed'

        data['rate'] = suppliers.get_supplier_max_price_for_domain(
            current_user.supplier_code,
            domain.name
        )

        categories.append(data)

        # sort by status
        categories_sorted = []
        categories_sorted += [x for x in categories if x['status'] == 'rejected']
        categories_sorted += [x for x in categories if x['status'] == 'draft']
        categories_sorted += [x for x in categories if x['status'] == 'submitted']
        categories_sorted += [x for x in categories if x['status'] == 'assessed']
        categories_sorted += [x for x in categories if x['status'] == 'unassessed']

    return jsonify(
        categories={
            'items': categories_sorted
        }
    ), 200


@api.route('/supplier/dashboard/user/<int:user_id>/deactivate', methods=['PUT'])
@login_required
@role_required('supplier')
def deactivate_user(user_id):
    if current_user.id == user_id:
        return jsonify(message='Cannot deactivate yourself'), 400

    user = users.find(
        id=user_id,
        active=True,
        role='supplier',
        supplier_code=current_user.supplier_code
    ).one_or_none()

    if not user:
        return jsonify(message='User not found'), 400

    user.active = False

    saved = users.save(user)
    return jsonify(user=saved)
