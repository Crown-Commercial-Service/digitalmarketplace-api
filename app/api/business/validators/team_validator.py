import collections
import pendulum
import re
from flask import current_app
from app.api.services import team_service
from app.api.helpers import get_email_domain


class TeamValidator(object):
    def __init__(self, team, current_user):
        self.team = team
        self.current_user = current_user
        self.domain = get_email_domain(current_user.email_address)

    def validate_all(self):
        result = (
            self.validate_basics() +
            self.validate_team_members()
        )
        warnings = [n for n in result if n.get('severity', 'error') == 'warning']
        errors = [n for n in result if n.get('severity', 'error') == 'error']
        validation_result = collections.namedtuple('Notification', ['warnings', 'errors'])
        return validation_result(warnings=warnings, errors=errors)

    def validate_basics(self):
        errors = []
        if not self.team.name or not self.team.name.replace(' ', ''):
            errors.append({
                'message': 'A team name is required.',
                'severity': 'error',
                'step': 'about',
                'id': 'T001'
            })

        if self.team.email_address:
            if '@' not in self.team.email_address or self.team.email_address.count('@') > 1:
                errors.append({
                    'message': 'Please add a valid email address.',
                    'severity': 'error',
                    'step': 'about',
                    'id': 'T002'
                })

            if get_email_domain(self.team.email_address) != self.domain:
                errors.append({
                    'message': 'You must use an email address ending in @{}.'.format(self.domain),
                    'severity': 'error',
                    'step': 'about',
                    'id': 'T003'
                })

        return errors

    def validate_team_members(self):
        errors = []

        if len(self.team.team_members) == 0:
            errors.append({
                'message': 'Team members are required.',
                'severity': 'error',
                'step': 'members',
                'id': 'TM001'
            })
            return errors

        if not any([tm for tm in self.team.team_members if tm.is_team_lead is True]):
            errors.append({
                'message': 'At least one team lead is required.',
                'severity': 'error',
                'step': 'leads',
                'id': 'TM002'
            })

        if not any([
            tm
            for tm in self.team.team_members
            if tm.is_team_lead is True and self.current_user.id == tm.user_id
        ]):
            errors.append({
                'message': 'You cannot remove yourself as a team lead.',
                'severity': 'error',
                'step': 'leads',
                'id': 'TM003'
            })

        for tm in self.team.team_members:
            teams = team_service.get_teams_for_user(tm.user_id)
            other_teams = [t for t in teams if t.id != self.team.id]
            if len(other_teams) > 0:
                errors.append({
                    'message': '{} is already a team member of {}.'.format(
                        tm.user.name,
                        ','.join([t.name for t in other_teams])
                    ),
                    'severity': 'error',
                    'step': 'members',
                    'id': 'TM004'
                })

            if tm.user.role != 'buyer':
                errors.append({
                    'message': '{} must be a buyer.'.format(tm.user.name),
                    'severity': 'error',
                    'step': 'members',
                    'id': 'TM005'
                })

            tm_email_domain = tm.user.email_address[tm.user.email_address.index('@'):]
            current_user_email_domain = self.current_user.email_address[self.current_user.email_address.index('@'):]
            if tm_email_domain != current_user_email_domain:
                errors.append({
                    'message': 'unable to add user id "{}" because they are from another agency.'.format(tm.user.id),
                    'severity': 'error',
                    'step': 'members',
                    'id': 'TM006'
                })

        return errors
