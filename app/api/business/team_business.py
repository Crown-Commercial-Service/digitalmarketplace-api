from collections import namedtuple

from flask_login import current_user

from app.api.business.errors import (NotFoundError, TeamError,
                                     UnauthorisedError, ValidationError)
from app.api.business.validators import TeamValidator
from app.api.services import (agency_service, audit_service, audit_types,
                              team_member_permission_service,
                              team_member_service, team_service, users)
from app.emails.teams import (send_removed_team_member_notification_emails,
                              send_request_access_email,
                              send_team_lead_notification_emails,
                              send_team_member_notification_emails)
from app.models import Team, TeamMember, TeamMemberPermission, permission_types
from app.tasks import publish_tasks


def create_team():
    user = users.get(current_user.id)
    created_teams = team_service.get_teams_for_user(user.id, 'created')
    completed_teams = team_service.get_teams_for_user(user.id)

    if len(completed_teams) == 0:
        if len(created_teams) == 0:
            team = team_service.save(
                Team(
                    name='',
                    status='created',
                    team_members=[
                        TeamMember(
                            user_id=user.id,
                            is_team_lead=True
                        )
                    ]
                )
            )

            audit_service.log_audit_event(
                audit_type=audit_types.create_team,
                data={},
                db_object=team,
                user=current_user.email_address
            )

            publish_tasks.team.delay(
                publish_tasks.compress_team(team),
                'created'
            )

            return get_team(team.id)

        created_team = created_teams.pop()
        return get_team(created_team.id)
    else:
        team = completed_teams[0]
        raise TeamError('You can only be in one team. You\'re already a member of {}.'.format(team.name))


def get_teams_overview():
    teams_overview = {}
    user = users.get(current_user.id)
    completed_teams = team_service.get_teams_for_user(user.id)

    overview = team_service.get_teams_overview(user.id, user.agency_id)
    teams_overview.update(overview=overview)

    organisation = agency_service.get_agency_name(user.agency_id)
    teams_overview.update(organisation=organisation)

    completed_teams_count = len(completed_teams)
    teams_overview.update(completedTeamsCount=completed_teams_count)

    return teams_overview


def get_people_overview():
    people_overview = {}
    user = users.get(current_user.id)
    completed_teams = team_service.get_teams_for_user(user.id)

    people = users.get_buyer_team_members(user.agency_id)
    people_overview.update(users=people)

    organisation = agency_service.get_agency_name(user.agency_id)
    people_overview.update(organisation=organisation)

    completed_teams_count = len(completed_teams)
    people_overview.update(completedTeamsCount=completed_teams_count)

    return people_overview


def get_team(team_id, allow_anyone=None):
    team = team_service.get_team(team_id)
    if not team:
        raise NotFoundError('Team {} does not exist'.format(team_id))

    if allow_anyone is None:
        team_member = team_member_service.find(
            is_team_lead=True,
            team_id=team_id,
            user_id=current_user.id
        ).one_or_none()

        if not team_member:
            raise UnauthorisedError('Only team leads can edit a team')

    if team['teamMembers'] is not None:
        for user_id, team_member in team['teamMembers'].iteritems():
            missing_permissions = [permission for permission in permission_types
                                   if permission not in team_member['permissions']]

            for permission in missing_permissions:
                team_member['permissions'][permission] = False

    return team


def update_team(team_id, data):
    team = team_service.get_team_for_update(team_id)
    if not team:
        raise NotFoundError('Team {} does not exist'.format(team_id))

    if len([tm for tm in team.team_members if tm.user_id == current_user.id and tm.is_team_lead is True]) == 0:
        raise UnauthorisedError('Only team leads can edit a team')

    update_team_information(team, data)
    result = update_team_leads_and_members(team, data)
    update_permissions(team, data)

    create_team = data.get('createTeam', False)

    agency_domains = agency_service.get_agency_domains(current_user.agency_id)
    saved = False
    if create_team:
        validation_result = TeamValidator(team, current_user, agency_domains).validate_all()
        if len([e for e in validation_result.errors]) > 0:
            raise ValidationError([e for e in validation_result.errors])

        team.status = 'completed'
        team_service.save(team)
        saved = True

        send_team_lead_notification_emails(team_id)
        send_team_member_notification_emails(team_id)
    elif team.status == 'completed':
        validation_result = TeamValidator(team, current_user, agency_domains).validate_all()
        if len([e for e in validation_result.errors]) > 0:
            raise ValidationError([e for e in validation_result.errors])

        team_service.save(team)
        saved = True
        new_team_leads = result.get('new_team_leads', [])
        new_team_members = result.get('new_team_members', [])
        removed_team_members = result.get('removed_team_members', [])

        if len(new_team_leads) > 0:
            send_team_lead_notification_emails(team_id, new_team_leads)
        if len(new_team_members) > 0:
            send_team_member_notification_emails(team_id, new_team_members)
        if len(removed_team_members) > 0:
            send_removed_team_member_notification_emails(team_id, removed_team_members)
    elif team.status == 'created':
        validation_result = TeamValidator(team, current_user, agency_domains).validate_all()
        team_member_errors = [e for e in validation_result.errors if str(e.get('id')).startswith('TM')]
        if team_member_errors:
            raise ValidationError(team_member_errors)

        team_service.save(team)

    if saved:
        publish_tasks.team.delay(
            publish_tasks.compress_team(team),
            'updated'
        )

    return get_team(team_id)


def update_team_information(team, data):
    team.name = data.get('name')
    team.email_address = data.get('emailAddress')


def update_team_leads_and_members(team, data):
    incoming_team_leads = data.get('teamLeads', {})
    incoming_team_members = data.get('teamMembers', {})

    incoming_team_lead_ids = []
    if incoming_team_leads:
        incoming_team_lead_ids = [int(team_lead_id) for team_lead_id in incoming_team_leads]

    incoming_team_member_ids = []
    if incoming_team_members:
        incoming_team_member_ids = [int(team_member_id) for team_member_id in incoming_team_members]

    current_team_members = [tm.user_id for tm in team.team_members]
    new_team_leads = []
    new_team_members = []
    removed_team_members = []

    for tm in team.team_members:
        if tm.user_id in incoming_team_lead_ids:
            if tm.is_team_lead is False:
                tm.is_team_lead = True
                new_team_leads.append(tm.user_id)

        if tm.user_id in incoming_team_member_ids:
            if tm.is_team_lead is True:
                tm.is_team_lead = False

        if tm.user_id not in incoming_team_lead_ids + incoming_team_member_ids:
            removed_team_members.append(tm.user_id)

    for user_id in removed_team_members:
        team_member = team_member_service.find(
            team_id=team.id,
            user_id=user_id
        ).one_or_none()

        if team_member:
            team.team_members.remove(team_member)

    for user_id in incoming_team_lead_ids:
        if user_id not in current_team_members:
            team.team_members.append(
                TeamMember(
                    team_id=team.id,
                    user_id=user_id,
                    is_team_lead=True
                )
            )
            new_team_leads.append(user_id)

    for user_id in incoming_team_member_ids:
        if user_id not in current_team_members:
            team.team_members.append(
                TeamMember(
                    team_id=team.id,
                    user_id=user_id,
                    is_team_lead=False
                )
            )
            new_team_members.append(user_id)

    return {
        'new_team_leads': new_team_leads,
        'new_team_members': new_team_members,
        'removed_team_members': removed_team_members
    }


def update_permissions(team, data):
    incoming_team_members = data.get('teamMembers', {})
    if not incoming_team_members:
        return
    for tm in team.team_members:
        modify = []
        remove = []
        if tm.is_team_lead is True:
            for p in tm.permissions:
                remove.append(p)
        else:
            permissions = incoming_team_members.get(str(tm.user_id), {}).get('permissions', {})
            for p in permission_types:
                team_member_permission = next(iter([tmp for tmp in tm.permissions if tmp.permission == p]), None)
                if team_member_permission:
                    if permissions.get(p, False) is True:
                        modify.append(team_member_permission)
                    else:
                        remove.append(team_member_permission)
                else:
                    if permissions.get(p, False) is True:
                        modify.append(
                            TeamMemberPermission(
                                permission=p
                            )
                        )

        for m in modify:
            tm.permissions.append(m)
        for r in remove:
            tm.permissions.remove(r)


def get_user_teams(user_id):
    return team_service.get_user_teams(user_id)


def request_access(data):
    if data.get('permission') not in permission_types:
        raise ValidationError('Invalid permission')

    permission = str(data.get('permission')).replace('_', ' ')
    send_request_access_email(permission)


def search_team_members(current_user, agency_id, keywords=None, exclude=None):
    return team_service.search_team_members(current_user, agency_id, keywords, exclude)


def get_team_briefs(team_id):
    return team_service.get_team_briefs(team_id)


def get_teams_by_brief_id(brief_id):
    return team_service.get_teams_by_brief_id(brief_id)
