from sqlalchemy import and_, func, cast, desc, case, or_
from sqlalchemy.types import TEXT
from sqlalchemy.orm import joinedload, raiseload
from sqlalchemy.dialects.postgresql import aggregate_order_by
from app.api.helpers import Service
from app.models import Team, TeamBrief, TeamMember, TeamMemberPermission, User, db


class TeamService(Service):
    __model__ = Team

    def __init__(self, *args, **kwargs):
        super(TeamService, self).__init__(*args, **kwargs)

    def get_team_for_update(self, team_id):
        return (
            db
            .session
            .query(Team)
            .options(
                joinedload(Team.team_members)
                .joinedload(TeamMember.permissions),
                joinedload(Team.team_members)
                .joinedload(TeamMember.user)
            )
            .filter(Team.id == team_id)
            .one_or_none()
        )

    def get_teams_for_user(self, user_id, status='completed'):
        return (
            db
            .session
            .query(Team)
            .join(TeamMember)
            .filter(
                Team.status == status,
                TeamMember.user_id == user_id
            )
            .all()
        )

    def get_team(self, team_id):
        team_leads = (db.session
                        .query(TeamMember.team_id, User.id, User.name, User.email_address)
                        .join(User)
                        .filter(TeamMember.is_team_lead.is_(True))
                        .order_by(User.name)
                        .subquery())

        aggregated_team_leads = (db.session
                                   .query(team_leads.columns.team_id,
                                          func.json_object_agg(
                                              team_leads.columns.id,
                                              func.json_build_object(
                                                  'emailAddress', team_leads.columns.email_address,
                                                  'name', team_leads.columns.name
                                              )
                                          ).label('teamLeads'))
                                   .group_by(team_leads.columns.team_id)
                                   .subquery())

        team_members = (db.session
                          .query(TeamMember.id.label('team_member_id'),
                                 TeamMember.team_id,
                                 User.id,
                                 User.name,
                                 User.email_address)
                          .join(User)
                          .filter(TeamMember.is_team_lead.is_(False))
                          .order_by(User.name)
                          .subquery())

        team_member_permissions = (db.session
                                     .query(
                                         team_members,
                                         func.coalesce(
                                             func.json_object_agg(
                                                 TeamMemberPermission.permission, True
                                             ).filter(TeamMemberPermission.permission.isnot(None)), '{}'
                                         ).label('permissions'))
                                     .join(
                                         TeamMemberPermission,
                                         TeamMemberPermission.team_member_id == team_members.columns.team_member_id,
                                         isouter=True)
                                     .group_by(
                                         team_members.columns.team_member_id,
                                         team_members.columns.team_id,
                                         team_members.columns.id,
                                         team_members.columns.name,
                                         team_members.columns.email_address)
                                     .order_by(team_members.columns.name)
                                     .subquery())

        aggregated_team_members = (db.session
                                     .query(team_member_permissions.columns.team_id,
                                            func.json_object_agg(
                                                team_member_permissions.columns.id,
                                                func.json_build_object(
                                                    'emailAddress', team_member_permissions.columns.email_address,
                                                    'name', team_member_permissions.columns.name,
                                                    'permissions', team_member_permissions.columns.permissions
                                                )).label('teamMembers'))
                                     .group_by(team_member_permissions.columns.team_id)
                                     .subquery())

        team = (db.session
                  .query(Team.id, Team.name, func.coalesce(Team.email_address, '').label('emailAddress'), Team.status,
                         aggregated_team_leads.columns.teamLeads, aggregated_team_members.columns.teamMembers)
                  .join(aggregated_team_leads, aggregated_team_leads.columns.team_id == Team.id, isouter=True)
                  .join(aggregated_team_members, aggregated_team_members.columns.team_id == Team.id, isouter=True)
                  .filter(Team.id == team_id)
                  .one_or_none())

        return team._asdict() if team else None

    def get_user_teams(self, user_id):
        result = (
            db
            .session
            .query(
                Team.id,
                Team.name,
                TeamMember.is_team_lead,
                func.array_agg(cast(TeamMemberPermission.permission, TEXT)).label('permissions')
            )
            .join(TeamMember)
            .join(TeamMemberPermission, isouter=True)
            .filter(TeamMember.user_id == user_id)
            .filter(Team.status == 'completed')
            .group_by(Team.id, Team.name, TeamMember.is_team_lead)
            .all()
        )
        return [r._asdict() for r in result]

    def get_teams_overview(self, user_id, agency_id):
        teams_led_by_user = (
            db
            .session
            .query(TeamMember.team_id)
            .join(Team)
            .filter(
                Team.status == 'completed',
                TeamMember.user_id == user_id,
                TeamMember.is_team_lead.is_(True)
            )
            .subquery('teams_led_by_user')
        )

        team_leads = (
            db
            .session
            .query(
                TeamMember.team_id,
                func.array_agg(aggregate_order_by(User.name, User.name)).label('leads')
            )
            .join(User)
            .filter(
                TeamMember.is_team_lead.is_(True),
                User.agency_id == agency_id,
                User.role == 'buyer'
            )
            .group_by(TeamMember.team_id)
            .subquery('team_leads')
        )

        team_members = (
            db
            .session
            .query(
                TeamMember.team_id,
                func.array_agg(aggregate_order_by(User.name, User.name)).label('members')
            )
            .join(User)
            .filter(
                TeamMember.is_team_lead.is_(False),
                User.agency_id == agency_id,
                User.role == 'buyer'
            )
            .group_by(TeamMember.team_id)
            .subquery('team_members')
        )

        result = (
            db
            .session
            .query(
                Team.id,
                Team.name,
                team_leads.columns.leads,
                team_members.columns.members,
                case(
                    [(teams_led_by_user.columns.team_id.isnot(None), True)],
                    else_=False
                ).label('isTeamLead')
            )
            .join(team_leads, team_leads.columns.team_id == Team.id)
            .join(team_members, team_members.columns.team_id == Team.id, isouter=True)
            .join(teams_led_by_user, teams_led_by_user.columns.team_id == Team.id, isouter=True)
            .filter(Team.status == 'completed')
            .order_by(Team.name)
            .all()
        )

        return [r._asdict() for r in result]

    def search_team_members(self, current_user, agency_id, keywords=None, exclude=None):
        exclude = exclude if exclude else []

        subquery = (
            db
            .session
            .query(
                TeamMember.user_id
            )
            .join(Team, User)
            .filter(Team.status == 'completed')
            .filter(User.agency_id == agency_id)
            .subquery()
        )

        results = (
            db
            .session
            .query(
                User.name,
                User.email_address.label('email'),
                User.id
            )
            .filter(
                User.id != current_user.id,
                User.active.is_(True),
                User.agency_id == agency_id
            )
            .filter(User.role == current_user.role)
            .filter(User.id.notin_(exclude))
            .filter(User.id.notin_(subquery))
        )

        if keywords:
            results = results.filter(
                or_(
                    User.name.ilike('%{}%'.format(keywords.encode('utf-8'))),
                    User.email_address.ilike('%{}%'.format(keywords.encode('utf-8')))
                )
            )

        results = results.order_by(func.lower(User.name))
        return [r._asdict() for r in results]

    def get_team_briefs(self, team_id):
        result = (
            db
            .session
            .query(
                TeamBrief.brief_id,
                TeamBrief.user_id,
                User.name
            )
            .join(User)
            .filter(
                TeamBrief.team_id == team_id
            )
        )

        return [r._asdict() for r in result]

    def get_teams_by_brief_id(self, brief_id):
        result = (
            db
            .session
            .query(
                TeamBrief.team_id,
                TeamBrief.user_id,
                User.name,
                User.email_address
            )
            .join(User)
            .filter(TeamBrief.brief_id == brief_id)
            .all()
        )

        return [r._asdict() for r in result]
