from app.api.helpers import Service
from app.models import TeamMember, User, db


class TeamMemberService(Service):
    __model__ = TeamMember

    def __init__(self, *args, **kwargs):
        super(TeamMemberService, self).__init__(*args, **kwargs)

    def get_team_leads_by_user_id(self, team_id, user_ids):
        return (db.session
                  .query(TeamMember)
                  .filter(
                      TeamMember.team_id == team_id,
                      TeamMember.user_id.in_(user_ids),
                      TeamMember.is_team_lead.is_(True))
                  .all())

    def get_team_members_by_user_id(self, team_id, user_ids):
        return (db.session
                  .query(TeamMember)
                  .filter(
                      TeamMember.team_id == team_id,
                      TeamMember.user_id.in_(user_ids),
                      TeamMember.is_team_lead.is_(False))
                  .all())
