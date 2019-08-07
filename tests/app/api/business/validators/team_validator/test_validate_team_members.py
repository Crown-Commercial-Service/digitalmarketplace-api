import pytest

from app.api.business.validators import TeamValidator
from app.models import Team, TeamMember, User, db, utcnow
from tests.app.helpers import BaseApplicationTest


class TestTeamMemberValidation(BaseApplicationTest):
    def setup(self):
        super(TestTeamMemberValidation, self).setup()

    def test_team_fails_validation_with_empty_team_members(self, users, user, teams, team):
        errors = TeamValidator(team, user).validate_team_members()

        assert len(errors) == 1
        assert all(error['id'] in ['TM001'] for error in errors)

    def test_team_fails_validation_when_member_is_in_another_team(self, users, user, teams, team, team_members):
        db.session.add(
            TeamMember(
                team_id=2,
                user_id=2,
                is_team_lead=True
            )
        )

        errors = TeamValidator(team, user).validate_team_members()

        assert len(errors) == 1
        assert all(error['id'] in ['TM004'] for error in errors)

    def test_team_fails_validation_when_member_is_not_a_buyer(self, users, user, teams, team, team_members):
        seller = users.pop()
        seller.role = 'supplier'
        errors = TeamValidator(team, user).validate_team_members()

        assert len(errors) == 1
        assert all(error['id'] in ['TM005'] for error in errors)

    def test_team_fails_validation_when_member_has_different_email_domain(self, users, user, teams, team, team_members):
        buyer = users.pop()
        buyer.email_address = 'buyer@cloud.gov.au'
        errors = TeamValidator(team, user).validate_team_members()

        assert len(errors) == 1
        assert all(error['id'] in ['TM006'] for error in errors)
