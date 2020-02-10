import pendulum
import pytest

from app.api.services import frameworks_service, lots_service
from app.models import Brief, User, db


@pytest.fixture()
def briefs(app, users):
    framework = frameworks_service.find(slug='digital-marketplace').one_or_none()
    atm_lot = lots_service.find(slug='atm').one_or_none()
    rfx_lot = lots_service.find(slug='rfx').one_or_none()
    specialist_lot = lots_service.find(slug='specialist').one_or_none()
    training_lot = lots_service.find(slug='training2').one_or_none()

    with app.app_context():
        db.session.add(
            Brief(
                id=1,
                data={},
                framework=framework,
                lot=atm_lot,
                users=users,
                published_at=None,
                withdrawn_at=None
            )
        )

        db.session.add(
            Brief(
                id=2,
                data={},
                framework=framework,
                lot=rfx_lot,
                users=users,
                published_at=None,
                withdrawn_at=None
            )
        )

        db.session.add(
            Brief(
                id=3,
                data={},
                framework=framework,
                lot=specialist_lot,
                users=users,
                published_at=None,
                withdrawn_at=None
            )
        )

        db.session.add(
            Brief(
                id=4,
                data={},
                framework=framework,
                lot=training_lot,
                users=users,
                published_at=None,
                withdrawn_at=None
            )
        )

        db.session.commit()
        yield db.session.query(Brief).all()


@pytest.fixture()
def users(app):
    with app.app_context():
        db.session.add(
            User(
                id=2,
                name='Schmidt',
                email_address='schmidy@ng.gov.au',
                password='chutney',
                active=True,
                password_changed_at=pendulum.now('utc'),
                role='buyer'
            )
        )

        db.session.commit()

        yield db.session.query(User).all()
