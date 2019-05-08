from flask import jsonify
from flask_login import login_required, current_user
from app.api import api
from app.api.services import suppliers, users, supplier_domain_service
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
            'code': supplier.code
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
def get_team():
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


@api.route('/supplier/dashboard/services', methods=['GET'])
@login_required
@role_required('supplier')
def get_services():
    """Supplier dashboard (Services) (role=supplier)
    ---
    tags:
      - dashboard
    definitions:
      SellerDashboardServiceItems:
        type: object
        properties:
            teams:
              type: array
              items:
                $ref: '#/definitions/SellerDashboardServiceItem'
      SellerDashboardServiceItem:
        type: object
        properties:
          email:
            type: string
          name:
            type: string
    responses:
      200:
        description: Seller dashboard data for the 'Service' tab
        schema:
          $ref: '#/definitions/SellerDashboardServiceItems'
    """
    supplier_domains = supplier_domain_service.get_supplier_domains(current_user.supplier_code)

    return jsonify(
        services={
            'items': supplier_domains
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
