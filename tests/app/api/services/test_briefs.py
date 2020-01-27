import pendulum
import pytest

from app.api.services import briefs as briefs_service
from app.api.services import frameworks_service, lots_service
from app.models import Brief, User, db
from tests.app.helpers import BaseApplicationTest


class TestBriefsService(BaseApplicationTest):
    def setup(self):
        super(TestBriefsService, self).setup()

    @pytest.fixture()
    def brief(self, app, users):
        with app.app_context():
            now = pendulum.now('utc')
            framework = frameworks_service.find(slug='digital-marketplace').one_or_none()
            specialist_lot = lots_service.find(slug='specialist').one_or_none()

            brief = Brief(
                id=1,
                data={},
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

    def test_opportunity_is_closed_early(self, brief):
        original_questions_closed_at = brief.questions_closed_at
        original_closed_at = brief.closed_at
        assert brief.status == 'live'

        closed_brief = briefs_service.close_opportunity_early(brief)
        assert closed_brief.status == 'closed'
        assert closed_brief.questions_closed_at <= original_questions_closed_at
        assert closed_brief.closed_at <= original_closed_at

    def test_original_dates_are_retained_when_opportunity_closed_early(self, brief):
        original_questions_closed_at = brief.questions_closed_at
        original_closed_at = brief.closed_at

        closed_brief = briefs_service.close_opportunity_early(brief)
        assert closed_brief.data['originalQuestionsClosedAt'] == (
            original_questions_closed_at.to_iso8601_string(extended=True)
        )

        assert closed_brief.data['originalClosedAt'] == (
            original_closed_at.to_iso8601_string(extended=True)
        )
