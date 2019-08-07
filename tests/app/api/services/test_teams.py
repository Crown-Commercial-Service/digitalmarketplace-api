import pytest

from app.api.services import team_service
from app.models import Team, TeamMember, User, db, utcnow
from tests.app.helpers import BaseApplicationTest


class TestTeamService(BaseApplicationTest):
    def setup(self):
        super(TestTeamService, self).setup()

    @pytest.fixture()
    def team(self, app):
        with app.app_context():
            db.session.add(
                Team(
                    id=1,
                    name='Marketplace',
                    email_address='marketplace@digital.gov.au',
                    status='completed'
                )
            )

            db.session.commit()

            yield db.session.query(Team).first()

    @pytest.fixture()
    def team_members(self, app):
        with app.app_context():
            db.session.add(
                TeamMember(
                    team_id=1,
                    user_id=1,
                    is_team_lead=True
                )
            )

            db.session.add(
                TeamMember(
                    team_id=1,
                    user_id=2,
                    is_team_lead=False
                )
            )

            db.session.commit()

            yield db.session.query(TeamMember).all()

    @pytest.fixture()
    def users(self, app):
        with app.app_context():
            db.session.add(
                User(
                    id=1,
                    name='Muu Muu',
                    email_address='muu@dta.gov.au',
                    password='muumuu',
                    active=True,
                    password_changed_at=utcnow(),
                    role='buyer'
                )
            )

            db.session.add(
                User(
                    id=2,
                    name='Moo Moo',
                    email_address='moo@dta.gov.au',
                    password='moomoo',
                    active=True,
                    password_changed_at=utcnow(),
                    role='buyer'
                )
            )

            db.session.commit()

            yield db.session.query(User).all()

    def test_get_team_returns_basic_details(self, team):
        team = team_service.get_team(1)

        assert team['emailAddress'] == 'marketplace@digital.gov.au'
        assert team['id'] == 1
        assert team['name'] == 'Marketplace'
        assert team['status'] == 'completed'

    def test_get_team_returns_team_leads(self, users, team, team_members):
        team = team_service.get_team(1)

        assert len(team['teamLeads'].keys()) == 1
        assert '1' in team['teamLeads']
        team_lead = team['teamLeads']['1']
        assert team_lead['emailAddress'] == 'muu@dta.gov.au'
        assert team_lead['name'] == 'Muu Muu'

    def test_get_team_returns_team_members(self, users, team, team_members):
        team = team_service.get_team(1)

        assert len(team['teamMembers'].keys()) == 1
        assert '2' in team['teamMembers']
        team_member = team['teamMembers']['2']
        assert team_member['emailAddress'] == 'moo@dta.gov.au'
        assert team_member['name'] == 'Moo Moo'
