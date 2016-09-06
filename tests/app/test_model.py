from datetime import datetime, timedelta
from collections import Counter

import mock
import pytest
from nose.tools import assert_equal, assert_raises
from sqlalchemy.exc import IntegrityError

from app import db, create_app
from app.models import (
    User, Lot, Framework, Service,
    Supplier, SupplierFramework,
    Brief, BriefResponse,
    ValidationError,
    BriefClarificationQuestion
)

from .helpers import BaseApplicationTest


def test_should_not_return_password_on_user():
    app = create_app('test')
    now = datetime.utcnow()
    user = User(
        email_address='email@digital.gov.au',
        name='name',
        role='buyer',
        password='password',
        active=True,
        failed_login_count=0,
        created_at=now,
        updated_at=now,
        password_changed_at=now,
        terms_accepted_at=now
    )

    with app.app_context():
        assert_equal(user.serialize()['emailAddress'], "email@digital.gov.au")
        assert_equal(user.serialize()['name'], "name")
        assert_equal(user.serialize()['role'], "buyer")
        assert_equal('password' in user.serialize(), False)


def test_framework_should_not_accept_invalid_status():
    app = create_app('test')
    with app.app_context(), assert_raises(ValidationError):
        f = Framework(
            name='foo',
            slug='foo',
            framework='g-cloud',
            status='invalid',
        )
        db.session.add(f)
        db.session.commit()


def test_framework_should_accept_valid_statuses():
    app = create_app('test')
    with app.app_context():
        for i, status in enumerate(Framework.STATUSES):
            f = Framework(
                name='foo',
                slug='foo-{}'.format(i),
                framework='g-cloud',
                status=status,
            )
            db.session.add(f)
            db.session.commit()


class TestBriefs(BaseApplicationTest):
    def setup(self):
        super(TestBriefs, self).setup()
        with self.app.app_context():
            self.framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
            self.lot = self.framework.get_lot('digital-outcomes')

    def test_create_a_new_brief(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot)
            db.session.add(brief)
            db.session.commit()

            assert isinstance(brief.created_at, datetime)
            assert isinstance(brief.updated_at, datetime)
            assert brief.id is not None
            assert brief.data == dict()

    def test_updating_a_brief_updates_dates(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot)
            db.session.add(brief)
            db.session.commit()

            updated_at = brief.updated_at
            created_at = brief.created_at

            brief.data = {'foo': 'bar'}
            db.session.add(brief)
            db.session.commit()

            assert brief.created_at == created_at
            assert brief.updated_at > updated_at

    def test_update_from_json(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot)
            db.session.add(brief)
            db.session.commit()

            updated_at = brief.updated_at
            created_at = brief.created_at

            brief.update_from_json({"foo": "bar"})
            db.session.add(brief)
            db.session.commit()

            assert brief.created_at == created_at
            assert brief.updated_at > updated_at
            assert brief.data == {'foo': 'bar'}

    def test_foreign_fields_stripped_from_brief_data(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)
        brief.data = {
            'frameworkSlug': 'test',
            'frameworkName': 'test',
            'lot': 'test',
            'lotName': 'test',
            'title': 'test',
        }

        assert brief.data == {'title': 'test'}

    def test_nulls_are_stripped_from_brief_data(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)
        brief.data = {'foo': 'bar', 'bar': None}

        assert brief.data == {'foo': 'bar'}

    def test_whitespace_values_are_stripped_from_brief_data(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)
        brief.data = {'foo': ' bar ', 'bar': '', 'other': '  '}

        assert brief.data == {'foo': 'bar', 'bar': '', 'other': ''}

    def test_status_defaults_to_draft(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)
        assert brief.status == 'draft'

    def test_query_draft_brief(self):
        with self.app.app_context():
            db.session.add(Brief(data={}, framework=self.framework, lot=self.lot))
            db.session.commit()

            assert Brief.query.filter(Brief.status == 'draft').count() == 1
            assert Brief.query.filter(Brief.status == 'live').count() == 0
            assert Brief.query.filter(Brief.status == 'withdrawn').count() == 0
            assert Brief.query.filter(Brief.status == 'closed').count() == 0

            # Check python implementation gives same result as the sql implementation
            assert Brief.query.all()[0].status == 'draft'

    def test_query_live_brief(self):
        with self.app.app_context():
            db.session.add(Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime.utcnow()))
            db.session.commit()

            assert Brief.query.filter(Brief.status == 'draft').count() == 0
            assert Brief.query.filter(Brief.status == 'live').count() == 1
            assert Brief.query.filter(Brief.status == 'withdrawn').count() == 0
            assert Brief.query.filter(Brief.status == 'closed').count() == 0

            # Check python implementation gives same result as the sql implementation
            assert Brief.query.all()[0].status == 'live'

    def test_query_withdrawn_brief(self):
        with self.app.app_context():
            db.session.add(Brief(
                data={}, framework=self.framework, lot=self.lot,
                published_at=datetime.utcnow() - timedelta(days=1), withdrawn_at=datetime.utcnow()
            ))
            db.session.commit()

            assert Brief.query.filter(Brief.status == 'draft').count() == 0
            assert Brief.query.filter(Brief.status == 'live').count() == 0
            assert Brief.query.filter(Brief.status == 'withdrawn').count() == 1
            assert Brief.query.filter(Brief.status == 'closed').count() == 0

            # Check python implementation gives same result as the sql implementation
            assert Brief.query.all()[0].status == 'withdrawn'

    def test_query_closed_brief(self):
        with self.app.app_context():
            db.session.add(Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1)))
            db.session.commit()

            assert Brief.query.filter(Brief.status == 'draft').count() == 0
            assert Brief.query.filter(Brief.status == 'live').count() == 0
            assert Brief.query.filter(Brief.status == 'withdrawn').count() == 0
            assert Brief.query.filter(Brief.status == 'closed').count() == 1

            # Check python implementation gives same result as the sql implementation
            assert Brief.query.all()[0].status == 'closed'

    def test_live_status_for_briefs_with_published_at(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime.utcnow())
        assert brief.status == 'live'

    def test_applications_closed_at_is_none_for_drafts(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)

        assert brief.applications_closed_at is None

    def test_closing_dates_are_set_with_published_at_when_no_requirements_length(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot,
                      published_at=datetime(2016, 3, 3, 12, 30, 1, 2))

        assert brief.applications_closed_at == datetime(2016, 3, 17, 23, 59, 59)
        assert brief.clarification_questions_closed_at == datetime(2016, 3, 10, 23, 59, 59)
        assert brief.clarification_questions_published_by == datetime(2016, 3, 16, 23, 59, 59)

    def test_closing_dates_are_set_with_published_at_when_requirements_length_is_two_weeks(self):
        brief = Brief(data={'requirementsLength': '2 weeks'}, framework=self.framework, lot=self.lot,
                      published_at=datetime(2016, 3, 3, 12, 30, 1, 2))

        assert brief.applications_closed_at == datetime(2016, 3, 17, 23, 59, 59)
        assert brief.clarification_questions_closed_at == datetime(2016, 3, 10, 23, 59, 59)
        assert brief.clarification_questions_published_by == datetime(2016, 3, 16, 23, 59, 59)

    def test_closing_dates_are_set_with_published_at_when_requirements_length_is_one_week(self):
        brief = Brief(data={'requirementsLength': '1 week'}, framework=self.framework, lot=self.lot,
                      published_at=datetime(2016, 3, 3, 12, 30, 1, 2))

        assert brief.applications_closed_at == datetime(2016, 3, 10, 23, 59, 59)
        assert brief.clarification_questions_closed_at == datetime(2016, 3, 7, 23, 59, 59)
        assert brief.clarification_questions_published_by == datetime(2016, 3, 9, 23, 59, 59)

    def test_query_brief_applications_closed_at_date_for_brief_with_no_requirements_length(self):
        with self.app.app_context():
            db.session.add(Brief(data={}, framework=self.framework, lot=self.lot,
                                 published_at=datetime(2016, 3, 3, 12, 30, 1, 2)))
            db.session.commit()
            assert Brief.query.filter(Brief.applications_closed_at == datetime(2016, 3, 17, 23, 59, 59)).count() == 1

    def test_query_brief_applications_closed_at_date_for_one_week_brief(self):
        with self.app.app_context():
            db.session.add(Brief(data={'requirementsLength': '1 week'}, framework=self.framework, lot=self.lot,
                                 published_at=datetime(2016, 3, 3, 12, 30, 1, 2)))
            db.session.commit()
            assert Brief.query.filter(Brief.applications_closed_at == datetime(2016, 3, 10, 23, 59, 59)).count() == 1

    def test_query_brief_applications_closed_at_date_for_two_week_brief(self):
        with self.app.app_context():
            db.session.add(Brief(data={'requirementsLength': '2 weeks'}, framework=self.framework, lot=self.lot,
                                 published_at=datetime(2016, 3, 3, 12, 30, 1, 2)))
            db.session.commit()
            assert Brief.query.filter(Brief.applications_closed_at == datetime(2016, 3, 17, 23, 59, 59)).count() == 1

    def test_query_brief_applications_closed_at_date_for_mix_of_brief_lengths(self):
        with self.app.app_context():
            db.session.add(Brief(data={'requirementsLength': '1 week'}, framework=self.framework, lot=self.lot,
                                 published_at=datetime(2016, 3, 10, 12, 30, 1, 2)))
            db.session.add(Brief(data={'requirementsLength': '2 weeks'}, framework=self.framework, lot=self.lot,
                                 published_at=datetime(2016, 3, 3, 12, 30, 1, 2)))
            db.session.add(Brief(data={}, framework=self.framework, lot=self.lot,
                                 published_at=datetime(2016, 3, 3, 12, 30, 1, 2)))
            db.session.commit()
            assert Brief.query.filter(Brief.applications_closed_at == datetime(2016, 3, 17, 23, 59, 59)).count() == 3

    def test_expired_status_for_a_brief_with_passed_close_date(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot,
                      published_at=datetime.utcnow() - timedelta(days=1000))

        assert brief.status == 'closed'
        assert brief.clarification_questions_are_closed
        assert brief.applications_closed_at < datetime.utcnow()

    def test_can_set_draft_brief_to_the_same_status(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)
        brief.status = 'draft'

    def test_publishing_a_brief_sets_published_at(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)
        assert brief.published_at is None

        brief.status = 'live'
        assert not brief.clarification_questions_are_closed
        assert isinstance(brief.published_at, datetime)

    def test_withdrawing_a_brief_sets_withdrawn_at(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime.utcnow())
        assert brief.withdrawn_at is None

        brief.status = 'withdrawn'
        assert isinstance(brief.withdrawn_at, datetime)

    def test_status_must_be_valid(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)

        with pytest.raises(ValidationError):
            brief.status = 'invalid'

    def test_cannot_set_live_brief_to_draft(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime.utcnow())

        with pytest.raises(ValidationError):
            brief.status = 'draft'

    def test_can_set_live_brief_to_withdrawn(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime.utcnow())
        brief.status = 'withdrawn'

        assert brief.published_at is not None
        assert brief.withdrawn_at is not None

    def test_cannot_set_brief_to_closed(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)

        with pytest.raises(ValidationError):
            brief.status = 'closed'

    def test_cannot_set_draft_brief_to_withdrawn(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)

        with pytest.raises(ValidationError):
            brief.status = 'withdrawn'

    def test_cannot_change_status_of_withdrawn_brief(self):
        brief = Brief(
            data={}, framework=self.framework, lot=self.lot,
            published_at=datetime.utcnow() - timedelta(days=1), withdrawn_at=datetime.utcnow()
        )

        for status in ['draft', 'live', 'closed']:
            with pytest.raises(ValidationError):
                brief.status = status

    def test_buyer_users_can_be_added_to_a_brief(self):
        with self.app.app_context():
            self.setup_dummy_user(role='buyer')

            brief = Brief(data={}, framework=self.framework, lot=self.lot,
                          users=User.query.all())

            assert len(brief.users) == 1

    def test_non_buyer_users_cannot_be_added_to_a_brief(self):
        with self.app.app_context():
            self.setup_dummy_user(role='admin')

            with pytest.raises(ValidationError):
                Brief(data={}, framework=self.framework, lot=self.lot,
                      users=User.query.all())

    def test_brief_lot_must_be_associated_to_the_framework(self):
        with self.app.app_context():
            other_framework = Framework.query.filter(Framework.slug == 'g-cloud-7').first()

            brief = Brief(data={}, framework=other_framework, lot=self.lot)
            db.session.add(brief)
            with pytest.raises(IntegrityError):
                db.session.commit()

    def test_brief_lot_must_require_briefs(self):
        with self.app.app_context():
            with pytest.raises(ValidationError):
                Brief(data={},
                      framework=self.framework,
                      lot=self.framework.get_lot('user-research-studios'))

    def test_cannot_update_lot_by_id(self):
        with self.app.app_context():
            with pytest.raises(ValidationError):
                Brief(data={},
                      framework=self.framework,
                      lot_id=self.framework.get_lot('user-research-studios').id)

    def test_add_brief_clarification_question(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot, status="live")
            db.session.add(brief)
            db.session.commit()

            brief.add_clarification_question(
                "How do you expect to deliver this?",
                "By the power of Grayskull")
            db.session.commit()

            assert len(brief.clarification_questions) == 1
            assert len(BriefClarificationQuestion.query.filter(
                BriefClarificationQuestion._brief_id == brief.id
            ).all()) == 1

    def test_new_clarification_questions_get_added_to_the_end(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot, status="live")
            db.session.add(brief)
            brief.add_clarification_question("How?", "This")
            brief.add_clarification_question("When", "Then")
            db.session.commit()

            assert brief.clarification_questions[0].question == "How?"
            assert brief.clarification_questions[1].question == "When"

    def test_copy_brief(self):
        with self.app.app_context():
            self.framework.status = 'live'
            self.setup_dummy_user(role='buyer')

            brief = Brief(
                data={'title': 'my title'},
                framework=self.framework,
                lot=self.lot,
                users=User.query.all()
            )

        copy = brief.copy()

        assert brief.data == {'title': 'my title'}
        assert brief.framework == copy.framework
        assert brief.lot == copy.lot
        assert brief.users == copy.users

    def test_copy_brief_raises_error_if_framework_is_not_live(self):
        brief = Brief(
            data={},
            framework=self.framework,
            lot=self.lot
        )
        with pytest.raises(ValidationError) as e:
            copy = brief.copy()

        assert str(e.value.message) == "Framework is not live"


class TestBriefResponses(BaseApplicationTest):
    def setup(self):
        super(TestBriefResponses, self).setup()
        with self.app.app_context():
            framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
            lot = framework.get_lot('digital-outcomes')
            self.brief = Brief(data={}, framework=framework, lot=lot)
            db.session.add(self.brief)
            db.session.commit()

            self.setup_dummy_suppliers(1)
            self.supplier = Supplier.query.filter(Supplier.code == 0).first()

    def test_create_a_new_brief_response(self):
        with self.app.app_context():
            brief_response = BriefResponse(data={}, brief=self.brief, supplier=self.supplier)
            db.session.add(brief_response)
            db.session.commit()

            assert brief_response.id is not None
            assert brief_response.supplier_code == 0
            assert brief_response.brief_id == self.brief.id
            assert isinstance(brief_response.created_at, datetime)
            assert brief_response.data == {}

    def test_foreign_fields_are_removed_from_brief_response_data(self):
        brief_response = BriefResponse(data={})
        brief_response.data = {'foo': 'bar', 'briefId': 5, 'supplierCode': 100}

        assert brief_response.data == {'foo': 'bar'}

    def test_nulls_are_removed_from_brief_response_data(self):
        brief_response = BriefResponse(data={})
        brief_response.data = {'foo': 'bar', 'bar': None}

        assert brief_response.data == {'foo': 'bar'}

    def test_whitespace_is_stripped_from_brief_response_data(self):
        brief_response = BriefResponse(data={})
        brief_response.data = {'foo': ' bar ', 'bar': ['', '  foo']}

        assert brief_response.data == {'foo': 'bar', 'bar': ['foo']}

    def test_brief_response_can_be_serialized(self):
        with self.app.app_context():
            brief_response = BriefResponse(data={'foo': 'bar'}, brief=self.brief, supplier=self.supplier)
            db.session.add(brief_response)
            db.session.commit()

            with mock.patch('app.models.url_for') as url_for:
                url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
                assert brief_response.serialize() == {
                    'id': brief_response.id,
                    'briefId': self.brief.id,
                    'supplierCode': 0,
                    'supplierName': 'Supplier 0',
                    'createdAt': mock.ANY,
                    'foo': 'bar',
                    'links': {
                        'self': (('.get_brief_response',), {'brief_response_id': brief_response.id}),
                        'brief': (('.get_brief',), {'brief_id': self.brief.id}),
                        'supplier': (('.get_supplier',), {'code': 0}),
                    }
                }


class TestBriefClarificationQuestion(BaseApplicationTest):
    def setup(self):
        super(TestBriefClarificationQuestion, self).setup()
        with self.app.app_context():
            self.framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
            self.lot = self.framework.get_lot('digital-outcomes')
            self.brief = Brief(data={}, framework=self.framework, lot=self.lot, status="live")
            db.session.add(self.brief)
            db.session.commit()

            # Reload objects after session commit
            self.framework = Framework.query.get(self.framework.id)
            self.lot = Lot.query.get(self.lot.id)
            self.brief = Brief.query.get(self.brief.id)

    def test_brief_must_be_live(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot, status="draft")
            with pytest.raises(ValidationError) as e:
                BriefClarificationQuestion(brief=brief, question="Why?", answer="Because")

            assert str(e.value.message) == "Brief status must be 'live', not 'draft'"

    def test_cannot_update_brief_by_id(self):
        with self.app.app_context(), pytest.raises(ValidationError) as e:
            BriefClarificationQuestion(brief_id=self.brief.id, question="Why?", answer="Because")

        assert str(e.value.message) == "Cannot update brief_id directly, use brief relationship"

    def test_published_at_is_set_on_creation(self):
        with self.app.app_context():
            question = BriefClarificationQuestion(
                brief=self.brief, question="Why?", answer="Because")

            db.session.add(question)
            db.session.commit()

            assert isinstance(question.published_at, datetime)

    def test_question_must_not_be_null(self):
        with self.app.app_context(), pytest.raises(IntegrityError):
            question = BriefClarificationQuestion(brief=self.brief, answer="Because")

            db.session.add(question)
            db.session.commit()

    def test_question_must_not_be_empty(self):
        with self.app.app_context(), pytest.raises(ValidationError) as e:
            question = BriefClarificationQuestion(brief=self.brief, question="", answer="Because")
            question.validate()

        assert e.value.message["question"] == "answer_required"

    def test_questions_must_not_be_more_than_100_words(self):
        long_question = " ".join(["word"] * 101)
        with self.app.app_context(), pytest.raises(ValidationError) as e:
            question = BriefClarificationQuestion(brief=self.brief, question=long_question, answer="Because")
            question.validate()

        assert e.value.message["question"] == "under_100_words"

    def test_question_must_not_be_more_than_5000_characters(self):
        long_question = "a" * 5001
        with self.app.app_context(), pytest.raises(ValidationError) as e:
            question = BriefClarificationQuestion(brief=self.brief, question=long_question, answer="Because")
            question.validate()

        assert e.value.message["question"] == "under_character_limit"

    def test_questions_can_be_100_words(self):
        question = " ".join(["word"] * 100)
        with self.app.app_context():
            question = BriefClarificationQuestion(brief=self.brief, question=question, answer="Because")
            question.validate()

    def test_answer_must_not_be_null(self):
        with self.app.app_context(), pytest.raises(IntegrityError):
            question = BriefClarificationQuestion(brief=self.brief, question="Why?")

            db.session.add(question)
            db.session.commit()

    def test_answer_must_not_be_empty(self):
        with self.app.app_context(), pytest.raises(ValidationError) as e:
            question = BriefClarificationQuestion(brief=self.brief, question="Why?", answer="")
            question.validate()

        assert e.value.message["answer"] == "answer_required"

    def test_answers_must_not_be_more_than_100_words(self):
        long_answer = " ".join(["word"] * 101)
        with self.app.app_context(), pytest.raises(ValidationError) as e:
            question = BriefClarificationQuestion(brief=self.brief, question="Why?", answer=long_answer)
            question.validate()

        assert e.value.message["answer"] == "under_100_words"

    def test_answer_must_not_be_more_than_5000_characters(self):
        long_answer = "a" * 5001
        with self.app.app_context(), pytest.raises(ValidationError) as e:
            question = BriefClarificationQuestion(brief=self.brief, question="Why?", answer=long_answer)
            question.validate()

        assert e.value.message["answer"] == "under_character_limit"

    def test_answers_can_be_100_words(self):
        answer = " ".join(["word"] * 100)
        with self.app.app_context():
            question = BriefClarificationQuestion(brief=self.brief, question="Why?", answer=answer)
            question.validate()


class TestServices(BaseApplicationTest):
    def test_framework_is_live_only_returns_live_frameworks(self):
        with self.app.app_context():
            self.setup_dummy_service(
                service_id='1000000000',
                status='published',
                framework_id=2)
            self.setup_dummy_services_including_unpublished(1)

            services = Service.query.framework_is_live()

            assert_equal(Service.query.count(), 4)
            assert_equal(services.count(), 3)
            assert (all(s.framework.status == 'live' for s in services))

    def test_lot_must_be_associated_to_the_framework(self):
        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            self.setup_dummy_service(
                service_id='10000000001',
                supplier_code=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=1)  # SaaS
            with pytest.raises(IntegrityError) as excinfo:
                db.session.commit()

            assert 'not present in table "framework_lot"' in "{}".format(excinfo.value)

    def test_default_ordering(self):
        def add_service(service_id, framework_id, lot_id, service_name):
            self.setup_dummy_service(
                service_id=service_id,
                supplier_code=0,
                framework_id=framework_id,
                lot_id=lot_id,
                data={'serviceName': service_name})

        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            add_service('1000000990', 3, 3, 'zzz')
            add_service('1000000991', 3, 3, 'aaa')
            add_service('1000000992', 3, 1, 'zzz')
            add_service('1000000993', 1, 3, 'zzz')
            db.session.commit()

            services = Service.query.default_order()

            assert_equal(
                [s.service_id for s in services],
                ['1000000993', '1000000992', '1000000991', '1000000990'])

    def test_has_statuses(self):
        with self.app.app_context():
            self.setup_dummy_services_including_unpublished(1)

            services = Service.query.has_statuses('published')

            assert_equal(services.count(), 1)

    def test_in_lot(self):
        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            self.setup_dummy_service(
                service_id='10000000001',
                supplier_code=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=5)  # digital-outcomes
            self.setup_dummy_service(
                service_id='10000000002',
                supplier_code=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=6)  # digital-specialists
            self.setup_dummy_service(
                service_id='10000000003',
                supplier_code=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=6)  # digital-specialists

            services = Service.query.in_lot('digital-specialists')
            assert services.count() == 2

    def test_data_has_key(self):
        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            self.setup_dummy_service(
                service_id='10000000001',
                supplier_code=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=6,  # digital-specialists
                data={'key1': 'foo', 'key2': 'bar'})
            self.setup_dummy_service(
                service_id='10000000002',
                supplier_code=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=6,  # digital-specialists
                data={'key1': 'blah'})
            services = Service.query.data_has_key('key1')
            assert services.count() == 2

            services = Service.query.data_has_key('key2')
            assert services.count() == 1

            services = Service.query.data_has_key('key3')
            assert services.count() == 0

    def test_data_key_contains_value(self):
        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            self.setup_dummy_service(
                service_id='10000000001',
                supplier_code=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=6,  # digital-specialists
                data={'key1': ['foo1', 'foo2'], 'key2': ['bar1']})
            self.setup_dummy_service(
                service_id='10000000002',
                supplier_code=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=6,  # digital-specialists
                data={'key1': ['foo1', 'foo3']})
            services = Service.query.data_key_contains_value('key1', 'foo1')
            assert services.count() == 2

            services = Service.query.data_key_contains_value('key2', 'bar1')
            assert services.count() == 1

            services = Service.query.data_key_contains_value('key3', 'foo1')
            assert services.count() == 0

            services = Service.query.data_key_contains_value('key1', 'bar1')
            assert services.count() == 0

    def test_service_status(self):
        service = Service(status='enabled')

        assert_equal(service.status, 'enabled')

    def test_invalid_service_status(self):
        service = Service()
        with assert_raises(ValidationError):
            service.status = 'invalid'

    def test_has_statuses_should_accept_multiple_statuses(self):
        with self.app.app_context():
            self.setup_dummy_services_including_unpublished(1)

            services = Service.query.has_statuses('published', 'disabled')

            assert_equal(services.count(), 2)

    def test_update_from_json(self):
        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            self.setup_dummy_service(
                service_id='1000000000',
                supplier_code=0,
                status='published',
                framework_id=2)

            service = Service.query.filter(Service.service_id == '1000000000').first()

            updated_at = service.updated_at
            created_at = service.created_at

            service.update_from_json({'foo': 'bar'})

            db.session.add(service)
            db.session.commit()

            assert service.created_at == created_at
            assert service.updated_at > updated_at
            assert service.data == {'foo': 'bar', 'serviceName': 'Service 1000000000'}


class TestSupplierFrameworks(BaseApplicationTest):
    def test_nulls_are_stripped_from_declaration(self):
        supplier_framework = SupplierFramework()
        supplier_framework.declaration = {'foo': 'bar', 'bar': None}

        assert supplier_framework.declaration == {'foo': 'bar'}

    def test_whitespace_values_are_stripped_from_declaration(self):
        supplier_framework = SupplierFramework()
        supplier_framework.declaration = {'foo': ' bar ', 'bar': '', 'other': ' '}

        assert supplier_framework.declaration == {'foo': 'bar', 'bar': '', 'other': ''}


class TestLot(BaseApplicationTest):
    def test_lot_data_is_serialized(self):
        with self.app.app_context():
            self.framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
            self.lot = self.framework.get_lot('user-research-studios')

            assert self.lot.serialize() == {
                u'id': 8,
                u'name': u'User research studios',
                u'slug': u'user-research-studios',
                u'allowsBrief': False,
                u'oneServiceLimit': False,
                u'unitSingular': u'lab',
                u'unitPlural': u'labs',
            }
