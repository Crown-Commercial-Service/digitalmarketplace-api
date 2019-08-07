import pytest

from app.models import Team, TeamMember, User, db, utcnow


@pytest.fixture()
def team(app):
    yield db.session.query(Team).first()


@pytest.fixture()
def teams(app):
    with app.app_context():
        db.session.add(
            Team(
                id=1,
                name='Marketplace',
                email_address='me@dta.gov.au',
                status='completed'
            )
        )

        db.session.add(
            Team(
                id=2,
                name='Cloud',
                email_address='cloud@dta.gov.au',
                status='completed'
            )
        )

        db.session.commit()

        yield db.session.query(Team).all()


@pytest.fixture()
def team_members(app):
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
def user(app):
    yield User.query.first()


@pytest.fixture()
def users(app):
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
