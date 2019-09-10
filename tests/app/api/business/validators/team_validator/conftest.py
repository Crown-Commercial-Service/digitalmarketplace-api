import pytest

from app.models import Agency, AgencyDomain, Team, TeamMember, User, db, utcnow


@pytest.fixture()
def agencies(app):
    with app.app_context():
        if not db.session.query(Agency).filter(Agency.id == 10).one_or_none():
            db.session.add(Agency(
                id=10,
                name='Team Test Agency',
                domain='teamtest.gov.au',
                category='Commonwealth',
                whitelisted=True,
                domains=[AgencyDomain(
                    domain='teamtest.gov.au',
                    active=True
                )]
            ))

            db.session.add(Agency(
                id=11,
                name='Team Test Agency 2',
                domain='teamtest2.gov.au',
                category='Commonwealth',
                whitelisted=True,
                domains=[AgencyDomain(
                    domain='teamtest2.gov.au',
                    active=True
                )]
            ))

            db.session.commit()
        yield Agency.query.all()


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
                email_address='me@teamtest.gov.au',
                status='completed'
            )
        )

        db.session.add(
            Team(
                id=2,
                name='Cloud',
                email_address='cloud@teamtest.gov.au',
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
def users(app, agencies):
    with app.app_context():
        db.session.add(
            User(
                id=1,
                name='Muu Muu',
                email_address='muu@dta.gov.au',
                password='muumuu',
                active=True,
                password_changed_at=utcnow(),
                role='buyer',
                agency_id=10
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
                role='buyer',
                agency_id=10
            )
        )

        db.session.commit()

        yield db.session.query(User).all()
