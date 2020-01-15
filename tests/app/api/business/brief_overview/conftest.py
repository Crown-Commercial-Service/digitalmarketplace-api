import mock
import pendulum
import pytest
from flask_login import current_user

from app.api.services import frameworks_service, lots_service
from app.models import (Brief, BriefResponse, Framework, Lot, Supplier, User,
                        WorkOrder, db)


@pytest.fixture()
def briefs(app, users):
    now = pendulum.now('utc')
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
                lot=specialist_lot,
                users=users,
                published_at=None,
                withdrawn_at=None
            )
        )

        published_atm = Brief(
            id=2,
            data={},
            framework=framework,
            lot=atm_lot,
            users=users,
            published_at=now.subtract(days=2),
            withdrawn_at=None
        )

        published_atm.questions_closed_at = now.add(days=3)
        published_atm.closed_at = now.add(days=5)
        db.session.add(published_atm)

        published_rfx_open_to_one = Brief(
            id=3,
            data={
                'sellerSelector': 'oneSeller',
                'sellers': {
                    '123': {
                        'name': 'FriendFace'
                    }
                }
            },
            framework=framework,
            lot=rfx_lot,
            users=users,
            published_at=now.subtract(days=2),
            withdrawn_at=None
        )

        published_rfx_open_to_one.questions_closed_at = now.add(days=3)
        published_rfx_open_to_one.closed_at = now.add(days=5)
        db.session.add(published_rfx_open_to_one)

        published_training_open_to_one = Brief(
            id=4,
            data={
                'sellerSelector': 'oneSeller',
                'sellers': {
                    '123': {
                        'name': 'FriendFace'
                    }
                }
            },
            framework=framework,
            lot=training_lot,
            users=users,
            published_at=now.subtract(days=2),
            withdrawn_at=None
        )

        published_training_open_to_one.questions_closed_at = now.add(days=3)
        published_training_open_to_one.closed_at = now.add(days=5)
        db.session.add(published_training_open_to_one)

        published_specialist_open_to_some = Brief(
            id=5,
            data={
                'numberOfSuppliers': '3',
                'sellerSelector': 'someSellers',
                'sellers': {
                    '123': {
                        'name': 'FriendFace'
                    }
                }
            },
            framework=framework,
            lot=specialist_lot,
            users=users,
            published_at=now.subtract(days=2),
            withdrawn_at=None
        )

        published_specialist_open_to_some.questions_closed_at = now.add(days=3)
        published_specialist_open_to_some.closed_at = now.add(days=5)
        db.session.add(published_specialist_open_to_some)

        closed_specialist = Brief(
            id=6,
            data={},
            framework=framework,
            lot=specialist_lot,
            users=users,
            created_at=now.subtract(days=3),
            published_at=now.subtract(days=3),
            withdrawn_at=None
        )

        closed_specialist.questions_closed_at = now.subtract(days=2)
        closed_specialist.closed_at = now.subtract(days=1)
        db.session.add(closed_specialist)

        withdrawn_specialist = Brief(
            id=7,
            data={},
            framework=framework,
            lot=specialist_lot,
            users=users,
            created_at=now.subtract(days=2),
            published_at=now.subtract(days=3),
            withdrawn_at=None
        )

        withdrawn_specialist.questions_closed_at = now.add(days=3)
        withdrawn_specialist.closed_at = now.add(days=5)
        withdrawn_specialist.withdrawn_at = now
        db.session.add(withdrawn_specialist)

        db.session.commit()
        yield db.session.query(Brief).all()


@pytest.fixture()
def brief_responses(app, briefs, suppliers):
    with app.app_context():
        now = pendulum.now('utc')

        db.session.add(
            BriefResponse(
                id=1,
                brief_id=3,
                data={},
                submitted_at=now,
                supplier_code=123
            )
        )

        db.session.add(
            BriefResponse(
                id=2,
                brief_id=4,
                data={},
                submitted_at=now,
                supplier_code=123
            )
        )

        db.session.add(
            BriefResponse(
                id=3,
                brief_id=5,
                data={},
                submitted_at=now,
                supplier_code=123
            )
        )

        db.session.add(
            BriefResponse(
                id=4,
                brief_id=5,
                data={},
                submitted_at=now,
                supplier_code=123
            )
        )

        db.session.add(
            BriefResponse(
                id=5,
                brief_id=5,
                data={},
                submitted_at=now,
                supplier_code=123
            )
        )

        db.session.commit()
        yield db.session.query(BriefResponse).all()


@pytest.fixture()
def suppliers(app):
    with app.app_context():
        db.session.add(
            Supplier(
                id=1,
                code=123,
                name='FriendFace',
                is_recruiter=False,
                data={}
            )
        )

        db.session.add(
            Supplier(
                id=2,
                code=456,
                name='FriendFlutter',
                is_recruiter=False,
                data={}
            )
        )

        db.session.commit()

        yield db.session.query(Supplier).all()


@pytest.fixture()
def users(app):
    with app.app_context():
        db.session.add(
            User(
                id=1,
                name='Maurice Moss',
                email_address='moss@ri.gov.au',
                password='mossman',
                active=True,
                password_changed_at=pendulum.now('utc'),
                role='buyer'
            )
        )

        db.session.commit()

        yield db.session.query(User).all()


@pytest.fixture()
def framework():
    return Framework(id=1, slug='digital-marketplace')


@pytest.fixture()
def work_order():
    return WorkOrder(id=1)


@pytest.fixture()
def outcome_lot():
    return Lot(id=1, slug='digital-outcome', one_service_limit=True)


@pytest.fixture()
def specialist_lot():
    return Lot(id=1, slug='digital-professionals', one_service_limit=True)


@pytest.fixture()
def outcome_brief(framework, outcome_lot):
    return Brief(id=1, data={}, framework=framework, lot=outcome_lot, work_order=None)


@pytest.fixture()
def specialist_brief(framework, specialist_lot):
    return Brief(id=1, data={}, framework=framework, lot=specialist_lot, work_order=None)
