from flask import jsonify
from flask_login import login_required, current_user
from app.api import api
from app.api.services import briefs, suppliers, users
from app.api.helpers import get_email_domain, role_required


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
    organisation = users.get_user_organisation(get_email_domain(current_user.email_address))
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
    organisation = users.get_user_organisation(get_email_domain(current_user.email_address))
    team_briefs = briefs.get_team_briefs(current_user.get_id(), get_email_domain(current_user.email_address))

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
    organisation = users.get_user_organisation(get_email_domain(current_user.email_address))
    team_members = users.get_team_members(current_user.get_id(), get_email_domain(current_user.email_address))

    return jsonify(items=team_members, organisation=organisation), 200
