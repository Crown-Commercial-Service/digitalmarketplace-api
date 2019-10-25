from flask import jsonify, abort, current_app, request
from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import aggregate_order_by
from app.api.helpers import Service
from app.models import Team, TeamMember, TeamMemberPermission, User, db

from app.api.business import (team_business)
from app.tasks import publish_tasks
from .. import main
from ... import db
from ...models import (
    User,
    Brief,
    TeamBrief,
    Team
)


@main.route('/admin/team', methods=['GET'])
def get_teams():
    teams = team_business.get_list_of_teams()
    return jsonify(teams=teams)


@main.route('/admin/team/<int:team_id>', methods=['GET'])
def get_team(team_id):
    team = team_business.get_team(team_id, True)
    briefs = team_business.get_team_briefs(team_id)
    return jsonify(team=team, briefs=briefs)


@main.route('/admin/buyers/<int:brief_id>/teams', methods=['GET'])
def get_teams_by_brief_id(brief_id):
    return jsonify(team_business.get_teams_by_brief_id(brief_id))
