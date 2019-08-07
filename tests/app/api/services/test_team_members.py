import pytest

from app.api.services import team_member_service
from app.models import Team, TeamMember, User, db, utcnow
from tests.app.helpers import BaseApplicationTest


class TestTeamMemberService(BaseApplicationTest):
    def setup(self):
        super(TestTeamMemberService, self).setup()

    @pytest.fixture()
    def teams(self, app):
        with app.app_context():
            db.session.add(
                Team(
                    id=1,
                    name='Marketplace',
                    email_address='me@digital.gov.au',
                    status='completed'
                )
            )

            db.session.add(
                Team(
                    id=2,
                    name='Cloud',
                    email_address='cloud@digital.gov.au',
                    status='completed'
                )
            )

            db.session.commit()

            yield db.session.query(Team).all()

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
                    is_team_lead=True
                )
            )

            db.session.add(
                TeamMember(
                    team_id=1,
                    user_id=3,
                    is_team_lead=False
                )
            )

            db.session.add(
                TeamMember(
                    team_id=2,
                    user_id=2,
                    is_team_lead=True
                )
            )

            db.session.add(
                TeamMember(
                    team_id=2,
                    user_id=3,
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

            db.session.add(
                User(
                    id=3,
                    name='Myu Myu',
                    email_address='myu@dta.gov.au',
                    password='myumyu',
                    active=True,
                    password_changed_at=utcnow(),
                    role='buyer'
                )
            )

            db.session.commit()

            yield db.session.query(User).all()

    def test_team_leads_are_returned_for_provided_user_ids(self, users, teams, team_members):
        team_leads = team_member_service.get_team_leads_by_user_id(1, [1, 2, 3])

        assert len(team_leads) == 2
        assert all(team_lead.user_id in [1, 2] for team_lead in team_leads)

    def test_team_members_are_returned_for_provided_user_ids(self, users, teams, team_members):
        team_members = team_member_service.get_team_members_by_user_id(1, [1, 2, 3])

        assert len(team_members) == 1
        assert all(team_member.user_id in [3] for team_member in team_members)
