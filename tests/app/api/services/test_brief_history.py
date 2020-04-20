import pendulum
import pytest

from app.api.services import (brief_history_service, frameworks_service,
                              lots_service)
from app.models import Brief, BriefHistory, User, db
from tests.app.helpers import BaseApplicationTest


class TestBriefHistoryService(BaseApplicationTest):
    def setup(self):
        super(TestBriefHistoryService, self).setup()

    @pytest.fixture()
    def brief_history(self, app, brief):
        now = pendulum.now('utc')

        with app.app_context():
            db.session.add(
                BriefHistory(
                    id=1,
                    brief_id=1,
                    user_id=1,
                    edited_at=now,
                    data={}
                )
            )

            db.session.add(
                BriefHistory(
                    id=2,
                    brief_id=1,
                    user_id=1,
                    edited_at=now.add(minutes=5),
                    data={}
                )
            )

            db.session.add(
                BriefHistory(
                    id=3,
                    brief_id=1,
                    user_id=1,
                    edited_at=now.add(minutes=10),
                    data={}
                )
            )

            db.session.commit()

            yield db.session.query(BriefHistory).all()

    @pytest.fixture()
    def brief(self, app, users):
        with app.app_context():
            now = pendulum.now('utc')
            framework = frameworks_service.find(slug='digital-marketplace').one_or_none()
            specialist_lot = lots_service.find(slug='specialist').one_or_none()

            brief = Brief(
                id=1,
                data={
                    'openTo': 'selected',
                    'sellers': {
                        '123': {
                            'name': 'FriendFace'
                        },
                        '456': {
                            'name': 'FriendFlutter'
                        }
                    }
                },
                framework=framework,
                lot=specialist_lot,
                users=users,
                published_at=now.subtract(days=2),
                withdrawn_at=None
            )

            brief.questions_closed_at = now.add(days=3)
            brief.closed_at = now.add(days=5)
            db.session.add(brief)

            db.session.commit()
            yield db.session.query(Brief).first()

    @pytest.fixture()
    def users(self, app):
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

    def test_get_edits_returns_result_in_descending_order(self, brief_history, brief):
        history = brief_history_service.get_edits(brief.id)
        assert len(history) == 3
        assert history[0].edited_at > history[1].edited_at
        assert history[1].edited_at > history[2].edited_at

    def test_get_last_edited_date_returns_most_recent_edit_date(self, brief_history, brief):
        edited_at = pendulum.now('utc').add(minutes=20)

        db.session.add(
            BriefHistory(
                id=4,
                brief_id=1,
                user_id=1,
                edited_at=edited_at,
                data={}
            )
        )

        db.session.commit()

        last_edited_at = brief_history_service.get_last_edited_date(brief.id)
        assert last_edited_at == edited_at
