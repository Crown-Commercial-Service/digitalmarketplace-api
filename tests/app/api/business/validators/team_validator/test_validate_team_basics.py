import pytest

from app.api.business.validators import TeamValidator
from app.models import Team
from tests.app.helpers import BaseApplicationTest


class TestTeamBasicsValidation(BaseApplicationTest):
    def setup(self):
        super(TestTeamBasicsValidation, self).setup()

    def test_team_fails_validation_with_empty_name(self, users, user):
        team = Team(name='')
        errors = TeamValidator(team, user).validate_basics()

        assert len(errors) == 1
        assert any(error['id'] == 'T001' for error in errors)

    def test_team_fails_validation_with_null_name(self, users, user):
        team = Team(name=None)
        errors = TeamValidator(team, user).validate_basics()

        assert len(errors) == 1
        assert any(error['id'] == 'T001' for error in errors)

    def test_team_passes_validation_with_name_only(self, users, user):
        team = Team(name='Marketplace')
        errors = TeamValidator(team, user).validate_basics()

        assert len(errors) == 0

    @pytest.mark.parametrize('email_address', ['marketplacedta.gov.au', '@marketplace@dta.gov.au'])
    def test_team_fails_validation_with_bad_email_address(self, users, user, email_address):
        team = Team(
            name='Marketplace',
            email_address=email_address
        )

        errors = TeamValidator(team, user, ['teamtest.gov.au']).validate_basics()

        assert len(errors) >= 1
        assert any(error['id'] == 'T002' for error in errors)

    def test_team_fails_validation_when_email_domain_is_different_to_user_domain(self, users, user):
        team = Team(
            name='Marketplace',
            email_address='marketplace@digital.gov.au'
        )

        errors = TeamValidator(team, user, ['teamtest.gov.au']).validate_basics()

        assert len(errors) == 1
        assert any(error['id'] == 'T003' for error in errors)

    def test_team_passes_validation_with_name_and_email(self, users, user):
        team = Team(
            email_address='marketplace@teamtest.gov.au',
            name='Marketplace'
        )

        errors = TeamValidator(team, user, ['teamtest.gov.au']).validate_basics()

        assert len(errors) == 0
