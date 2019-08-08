from flask import current_app
from flask_login import current_user

from app.api.services import (audit_service, audit_types, team_member_service,
                              team_service, users)

from .util import escape_markdown, render_email_template, send_or_handle_error


def send_removed_team_member_notification_emails(team_id, user_ids):
    team = team_service.find(id=team_id).first()

    to_addresses = []
    for user_id in user_ids:
        user = users.get(user_id)
        to_addresses.append(user.email_address)

    if len(to_addresses) == 0:
        return

    email_body = render_email_template(
        'team_member_removed.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        team_lead=escape_markdown(current_user.name),
        team_name=escape_markdown(team.name)
    )

    subject = 'You have been removed from the {} team'.format(team.name.encode('utf-8'))

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='team member removed email'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.team_member_removed,
        data={
            'to_address': to_addresses,
            'subject': subject
        },
        db_object=team,
        user=''
    )


def send_team_lead_notification_emails(team_id, user_ids=None):
    team = team_service.find(id=team_id).first()

    if user_ids is None or len(user_ids) == 0:
        # Team leads added through the create flow
        team_leads = team_member_service.find(team_id=team_id, is_team_lead=True).all()
        team_leads = [team_lead for team_lead in team_leads if team_lead.user_id != current_user.id]
    else:
        # Team leads added through the edit flow
        team_leads = team_member_service.get_team_leads_by_user_id(team_id, user_ids)

    to_addresses = []
    for team_lead in team_leads:
        user = users.get(team_lead.user_id)
        to_addresses.append(user.email_address)

    if len(to_addresses) == 0:
        return

    email_body = render_email_template(
        'team_lead_added.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        team_name=escape_markdown(team.name)
    )

    subject = 'You have been upgraded to a team lead'

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='team lead added email'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.team_lead_added,
        data={
            'to_address': to_addresses
        },
        db_object=team,
        user=''
    )


def send_team_member_notification_emails(team_id, user_ids=None):
    team = team_service.find(id=team_id).first()

    if user_ids is None or len(user_ids) == 0:
        # Team members added through the create flow
        members = team_member_service.find(team_id=team_id, is_team_lead=False).all()
    else:
        # Team members added through the edit flow
        members = team_member_service.get_team_members_by_user_id(team_id, user_ids)

    to_addresses = []
    for member in members:
        user = users.get(member.user_id)
        to_addresses.append(user.email_address)

    if len(to_addresses) == 0:
        return

    email_body = render_email_template(
        'team_member_added.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        team_lead=escape_markdown(current_user.name),
        team_name=escape_markdown(team.name)
    )

    subject = '{} added you as a member of {}'.format(current_user.name, team.name.encode('utf-8'))

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='team member added email'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.team_member_added,
        data={
            'to_address': to_addresses,
            'subject': subject
        },
        db_object=team,
        user=''
    )


def send_request_access_email(permission):
    if not current_user.is_part_of_team():
        return

    user_team = current_user.get_team()

    team = team_service.find(
        id=user_team.get('id'),
        status='completed'
    ).one_or_none()

    if not team:
        return

    to_addresses = [tm.user.email_address for tm in team.team_members if tm.is_team_lead]

    if len(to_addresses) == 0:
        return

    email_body = render_email_template(
        'request_access.md',
        frontend_url=current_app.config['FRONTEND_ADDRESS'],
        name=escape_markdown(current_user.name),
        permission=escape_markdown(permission)
    )

    subject = '{} has requested a change to their permissions'.format(current_user.name)

    send_or_handle_error(
        to_addresses,
        email_body,
        subject,
        current_app.config['DM_GENERIC_NOREPLY_EMAIL'],
        current_app.config['DM_GENERIC_SUPPORT_NAME'],
        event_description_for_errors='request access email'
    )

    audit_service.log_audit_event(
        audit_type=audit_types.sent_request_access,
        data={
            'to_address': to_addresses,
            'subject': subject,
            'email_body': email_body
        },
        db_object=team,
        user=current_user.email_address
    )
