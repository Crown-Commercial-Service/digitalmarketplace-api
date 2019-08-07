import pytest

from app.api.business.validators import TeamValidator
from app.models import Team, TeamMember, User, db, utcnow
from tests.app.helpers import BaseApplicationTest


class TestTeamCreatorValidation(BaseApplicationTest):
    def setup(self):
        super(TestTeamCreatorValidation, self).setup()

    def test_team_fails_validation_with_no_team_lead(self, users, user, teams, team, team_members):
        team_members[0].is_team_lead = False
        result = TeamValidator(team, user).validate_all()

        assert len(result.errors) == 2
        assert any(error['id'] == 'TM002' for error in result.errors)
        assert any(error['id'] == 'TM003' for error in result.errors)
