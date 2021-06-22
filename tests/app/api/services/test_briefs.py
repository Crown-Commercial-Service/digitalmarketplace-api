import pendulum
import pytest

from app.api.business.brief import brief_business
from app.api.services import audit_types, brief_responses_service
from app.api.services import briefs as briefs_service
from app.api.services import frameworks_service, lots_service
from app.models import (AuditEvent, Brief, BriefQuestion, BriefResponse,
                        Supplier, User, db)
from tests.app.helpers import BaseApplicationTest


class TestBriefsService(BaseApplicationTest):
    def setup(self):
        super(TestBriefsService, self).setup()

    @pytest.fixture()
    def audit_event(self, app, brief_responses):
        with app.app_context():
            now = pendulum.now('utc')
            brief_response = brief_responses_service.get(2)

            db.session.add(
                AuditEvent(
                    audit_type=audit_types.create_brief_response,
                    data={},
                    db_object=brief_response,
                    user='draft@friendflutter.com.au'
                )
            )

            db.session.commit()
            yield db.session.query(AuditEvent).first()

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
    def brief_questions(self, app, brief):
        with app.app_context():
            now = pendulum.now('utc')

            db.session.add(
                BriefQuestion(
                    id=1,
                    answered=False,
                    brief_id=1,
                    created_at=now,
                    data={
                        'created_by': 'curious@friendface.com.au',
                        'question': 'What existed before the big bang?'
                    },
                    supplier_code=123
                )
            )

            db.session.add(
                BriefQuestion(
                    id=2,
                    answered=False,
                    brief_id=1,
                    created_at=now,
                    data={
                        'created_by': 'curious@friendflutter.com.au',
                        'question': 'Will there be another big bang?'
                    },
                    supplier_code=456
                )
            )

            db.session.commit()
            yield db.session.query(BriefQuestion).all()

    @pytest.fixture()
    def brief_responses(self, app, brief, suppliers):
        now = pendulum.now('utc')

        with app.app_context():
            db.session.add(
                BriefResponse(
                    id=1,
                    brief_id=1,
                    created_at=now,
                    data={
                        'respondToEmailAddress': 'submitted@friendface.com.au'
                    },
                    submitted_at=now,
                    supplier_code=123,
                    updated_at=now
                )
            )

            db.session.add(
                BriefResponse(
                    id=2,
                    brief_id=1,
                    created_at=now,
                    data={},
                    supplier_code=456,
                    updated_at=now
                )
            )

            db.session.commit()
            yield db.session.query(BriefResponse).all()

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

    @pytest.fixture()
    def suppliers(self, app):
        with app.app_context():
            db.session.add(
                Supplier(
                    id=1,
                    code=123,
                    name='FriendFace',
                    is_recruiter=False,
                    data={
                        'contact_email': 'biz.contact@friendface.com.au',
                        'email': 'authorised.rep@friendface.com.au'
                    }
                )
            )

            db.session.add(
                Supplier(
                    id=2,
                    code=456,
                    name='FriendFlutter',
                    is_recruiter=False,
                    data={
                        'email': 'authorised.rep@friendflutter.com.au'
                    }
                )
            )

            db.session.commit()

            yield db.session.query(Supplier).all()

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
            original_questions_closed_at.to_iso8601_string()
        )

        assert closed_brief.data['originalClosedAt'] == (
            original_closed_at.to_iso8601_string()
        )

    def test_opportunity_is_withdrawn(self, brief):
        assert brief.status == 'live'
        withdrawn_brief = briefs_service.withdraw_opportunity(brief, 'Project cancelled')
        assert withdrawn_brief.status == 'withdrawn'
        assert withdrawn_brief.withdrawn_at is not None

    def test_reason_is_retained_when_opportunity_is_withdrawn(self, brief):
        assert 'reasonToWithdraw' not in brief.data
        withdrawn_brief = briefs_service.withdraw_opportunity(brief, 'Project cancelled')
        assert withdrawn_brief.data['reasonToWithdraw'] == 'Project cancelled'

    def test_sellers_to_notify_includes_email_address_submitted_with_response(self, brief, brief_responses, suppliers):
        email_addresses = briefs_service.get_sellers_to_notify(brief, brief_business.is_open_to_all(brief))
        assert 'submitted@friendface.com.au' in email_addresses

    def test_sellers_to_notify_has_email_address_of_user_that_created_draft_response(self, audit_event, brief,
                                                                                     brief_responses, suppliers):
        email_addresses = briefs_service.get_sellers_to_notify(brief, brief_business.is_open_to_all(brief))
        assert 'draft@friendflutter.com.au' in email_addresses

    def test_sellers_to_notify_has_email_address_of_users_that_asked_questions(self, brief, brief_responses,
                                                                               brief_questions, suppliers):
        email_addresses = briefs_service.get_sellers_to_notify(brief, brief_business.is_open_to_all(brief))
        assert 'curious@friendface.com.au' in email_addresses
        assert 'curious@friendflutter.com.au' in email_addresses

    def test_sellers_to_notify_has_email_address_used_to_invite_sellers(self, brief, suppliers):
        email_addresses = briefs_service.get_sellers_to_notify(brief, brief_business.is_open_to_all(brief))
        assert 'biz.contact@friendface.com.au' in email_addresses
        assert 'authorised.rep@friendflutter.com.au' in email_addresses
