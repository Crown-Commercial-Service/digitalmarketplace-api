from flask import jsonify
from flask_login import login_required, current_user
from app.api import api
from app.api.services import briefs, suppliers, users
from app.api.helpers import get_user_email_domain, role_required


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


@api.route('/dashboard/my/briefs', methods=['GET'])
@login_required
@role_required('buyer')
def get_buyer_dashboard_data_for_my_briefs():
    """Buyer dashboard (My briefs) (role=buyer)
    ---
    tags:
      - dashboard
    definitions:
      BuyerDashboardItems:
        type: object
        properties:
            items:
              type: array
              items:
                $ref: '#/definitions/BuyerDashboardItem'
            organisation:
              type: string
      BuyerDashboardItem:
        type: object
        properties:
          applications:
            type: integer
          closed_at:
            type: string
            nullable: true
          framework:
            type: string
          id:
            type: integer
          lot:
            type: string
          name:
            type: string
          status:
            type: string
          work_order:
            type: integer
            nullable: true
    responses:
      200:
        description: Buyer dashboard data for the 'My briefs' tab
        schema:
          $ref: '#/definitions/BuyerDashboardItems'
    """
    organisation = users.get_user_organisation(get_user_email_domain())
    user_briefs = briefs.get_user_briefs(current_user.get_id())

    return jsonify(items=user_briefs, organisation=organisation), 200


@api.route('/dashboard/team/briefs', methods=['GET'])
@login_required
@role_required('buyer')
def get_buyer_dashboard_data_for_team_briefs():
    """Buyer dashboard (Team briefs) (role=buyer)
    ---
    tags:
      - dashboard
    definitions:
      BuyerDashboardTeamItems:
        type: object
        properties:
            items:
              type: array
              items:
                $ref: '#/definitions/BuyerDashboardTeamItem'
            organisation:
              type: string
      BuyerDashboardTeamItem:
        type: object
        properties:
          author:
            type: string
          closed_at:
            type: string
            nullable: true
          framework:
            type: string
          id:
            type: integer
          lot:
            type: string
          name:
            type: string
          status:
            type: string
    responses:
      200:
        description: Buyer dashboard data for the 'Team briefs' tab
        schema:
          $ref: '#/definitions/BuyerDashboardTeamItems'
    """
    organisation = users.get_user_organisation(get_user_email_domain())
    team_briefs = briefs.get_team_briefs(current_user.get_id(), get_user_email_domain())

    return jsonify(items=team_briefs, organisation=organisation), 200


@api.route('/dashboard/team/overview', methods=['GET'])
@login_required
@role_required('buyer')
def get_buyer_dashboard_data_for_team_overview():
    """Buyer dashboard (Team overview) (role=buyer)
    ---
    tags:
      - dashboard
    definitions:
      BuyerDashboardTeamOverviewItems:
        type: object
        properties:
            items:
              type: array
              items:
                $ref: '#/definitions/BuyerDashboardTeamOverviewItem'
            organisation:
              type: string
      BuyerDashboardTeamOverviewItem:
        type: object
        properties:
          email:
            type: string
          name:
            type: string
    responses:
      200:
        description: Buyer dashboard data for the 'Team overview' tab
        schema:
          $ref: '#/definitions/BuyerDashboardTeamOverviewItems'
    """
    organisation = users.get_user_organisation(get_user_email_domain())
    team_members = users.get_team_members(current_user.get_id(), get_user_email_domain())

    return jsonify(items=team_members, organisation=organisation), 200
