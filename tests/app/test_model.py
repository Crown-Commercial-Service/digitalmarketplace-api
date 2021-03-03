import json
from datetime import datetime as builtindatetime

import mock
import pendulum
import pytest
from nose.tools import assert_equal, assert_raises
from pendulum import create as datetime
from pendulum import interval
from pytest import raises
from sqlalchemy.exc import DataError, IntegrityError

from app import create_app, db
from app.datetime_utils import naive, utcnow
from app.models import (Address, Application, Brief,
                        BriefClarificationQuestion, BriefResponse, Domain,
                        Framework, Lot, MasterAgreement, Product,
                        RecruiterInfo, Service, SignedAgreement, Supplier,
                        SupplierDomain, SupplierFramework, User,
                        ValidationError, WorkOrder)

from .helpers import (INCOMING_APPLICATION_DATA, BaseApplicationTest,
                      setup_dummy_user)


def naive_datetime(*args, **kwargs):
    p = pendulum.create(*args, **kwargs)
    return naive(p)


def test_views(app_context):
    setup_dummy_user(role='buyer')

    u = User.query.first()
    u.email_address = 'abc@whatever.gov.au'
    db.session.flush()
    db.session.commit()
    assert u.viewrow().email_domain == 'whatever.gov.au'


def test_should_not_return_password_on_user():
    app = create_app('test')
    now = utcnow()
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


def test_product_models(app_context):
    address = Address(state='NSW', postal_code='1234')
    product = Product(name='product')

    supplier = Supplier(name='supplier', addresses=[address], products=[product])

    supplier.products = [product]
    db.session.add(supplier)
    db.session.commit()

    supplier = Supplier.query.all()[0]
    assert supplier.products == [product]

    db.session.delete(supplier)
    db.session.commit()

    # confirm associated objects are gone too
    assert Product.query.all() == []
    assert Address.query.all() == []

    JSON = {
        'name': 'product',
        'summary': 'summary of product'
    }

    assert Product.from_json(JSON).serializable == Product(**JSON).serializable


class TestBriefs(BaseApplicationTest):
    def setup(self):
        super(TestBriefs, self).setup()
        with self.app.app_context():
            self.framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
            self.lot = self.framework.get_lot('digital-outcomes')

    def test_brief_datetimes(self):
        TZ = 'Australia/Sydney'
        with self.app.app_context():
            for hour in range(24):
                NOW = SYDNEY = pendulum.create(2016, 1, 3, hour, tz=TZ)
                UTC = NOW.in_tz('UTC')
                SYDNEY_DAY = SYDNEY.date()
                CLOSING_DAY = SYDNEY_DAY + interval(weeks=1)
                CLOSING_AT = pendulum.create(2016, 1, 10, 18, 0, 0, tz=TZ)
                CLOSING_AT_UTC = CLOSING_AT.in_timezone('UTC')

                QUESTIONS_CLOSING_AT_1 = CLOSING_AT.subtract(days=7).add(days=2)
                QUESTIONS_CLOSING_AT_UTC_1 = QUESTIONS_CLOSING_AT_1.in_tz('UTC')

                assert SYDNEY_DAY.day == 3

                brief = Brief(data={}, framework=self.framework, lot=self.lot)

                db.session.add(brief)

                with pendulum.test(NOW):
                    db.session.commit()

                assert brief.created_at == NOW
                assert brief.requirements_length == '2 weeks'
                assert brief.questions_duration_workdays == 5

                assert brief.published_day is None
                assert brief.applications_closing_date is None
                assert brief.applications_closed_at is None
                assert brief.clarification_questions_published_by is None

                brief.data = {
                    'requirementsLength': '2 weeks'
                }

                assert brief.requirements_length == '2 weeks'
                assert brief.questions_duration_workdays == 5

                brief.data = {
                    'requirementsLength': '1 week'
                }

                brief.published_at = UTC
                db.session.commit()

                assert brief.requirements_length == '1 week'
                assert brief.questions_duration_workdays == 2

                assert brief.published_day == SYDNEY_DAY
                assert brief.applications_closing_date == CLOSING_DAY

                assert brief.applications_closed_at == \
                    CLOSING_AT_UTC

                by_pday = Brief.query.filter(
                    Brief.published_day == SYDNEY_DAY)
                brief = by_pday.one()
                assert brief.published_day == SYDNEY_DAY

                by_close_utc = Brief.query.filter(
                    Brief.applications_closed_at == naive(CLOSING_AT_UTC))

                brief = by_close_utc.one()
                assert brief.applications_closed_at == CLOSING_AT_UTC

                assert brief.clarification_questions_closed_at ==\
                    QUESTIONS_CLOSING_AT_UTC_1

                # day before is a saturday, so should return friday
                assert brief.clarification_questions_published_by ==\
                    CLOSING_AT_UTC.subtract(days=2)

                db.session.delete(brief)

    def test_create_a_new_brief(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot)
            db.session.add(brief)
            db.session.commit()

            assert isinstance(brief.created_at, builtindatetime)
            assert isinstance(brief.updated_at, builtindatetime)
            assert brief.id is not None
            assert brief.data == dict()

    def test_brief_domains(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot)
            db.session.add(brief)
            db.session.commit()

            assert brief.domain is None

            brief.data['specialistRole'] = 'userResearcher'
            db.session.commit()
            db.session.refresh(brief)

            assert brief.domain.name == 'User research and Design'

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
        with self.app.app_context():
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
            assert Brief.query.all()[0].published_day is None

    def test_query_live_brief(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=utcnow())
            brief.closed_at = utcnow().add(weeks=2)
            db.session.add(brief)
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
                published_at=utcnow() - interval(days=1), withdrawn_at=utcnow()
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
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=utcnow())
            assert brief.status == 'live'

    def test_applications_closed_at_is_none_for_drafts(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot)

            assert brief.applications_closed_at is None

    def test_closing_dates_are_set_with_published_at_when_no_requirements_length(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot,
                          published_at=datetime(2016, 3, 3, 12, 30, 1, 2))

            assert brief.applications_closed_at == datetime(2016, 3, 17, 7, 0, 0)
            assert brief.clarification_questions_closed_at == datetime(2016, 3, 10, 7, 0, 0)
            assert brief.clarification_questions_published_by == datetime(2016, 3, 16, 7, 0, 0)

    def test_closing_dates_are_set_with_published_at_when_requirements_length_is_two_weeks(self):
        with self.app.app_context():
            brief = Brief(data={'requirementsLength': '2 weeks'}, framework=self.framework, lot=self.lot,
                          published_at=datetime(2016, 3, 3, 12, 30, 1, 2))

            assert brief.applications_closed_at == datetime(2016, 3, 17, 7, 0, 0)
            assert brief.clarification_questions_closed_at == datetime(2016, 3, 10, 7, 0, 0)
            assert brief.clarification_questions_published_by == datetime(2016, 3, 16, 7, 0, 0)

    def test_closing_dates_are_set_with_published_at_when_requirements_length_is_one_week(self):
        with self.app.app_context():
            brief = Brief(data={'requirementsLength': '1 week'}, framework=self.framework, lot=self.lot)
            brief.published_at = datetime(2016, 3, 3, 12, 30, 1, 2)
            assert brief.applications_closed_at == datetime(2016, 3, 10, 7, 0, 0)
            assert brief.clarification_questions_closed_at == datetime(2016, 3, 7, 7, 0, 0)
            assert brief.clarification_questions_published_by == datetime(2016, 3, 9, 7, 0, 0)

    def test_query_brief_applications_closed_at_date_for_brief_with_no_requirements_length(self):
        with self.app.app_context():
            b = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2016, 3, 3, 12, 30, 1, 2))

            db.session.add(b)
            db.session.commit()

            apps_closed_py = b.applications_closed_at

            assert apps_closed_py.timezone.name == 'UTC'

            app_closed_query = db.session.query(Brief.applications_closed_at)

            apps_closed_sql = app_closed_query.first()[0]

            assert apps_closed_sql == apps_closed_py

            assert Brief.query.filter(Brief.applications_closed_at == naive_datetime(2016, 3, 17, 7, 0, 0)).count() == 1

    def test_query_brief_applications_closed_at_date_for_one_week_brief(self):
        with self.app.app_context():
            new_brief = Brief(data={'requirementsLength': '1 week'}, framework=self.framework, lot=self.lot)
            db.session.add(new_brief)
            db.session.commit()
            new_brief.published_at = datetime(2016, 3, 3, 12, 30, 1, 2)

            assert Brief.query.filter(Brief.applications_closed_at == naive_datetime(2016, 3, 10, 7, 0, 0)).count() == 1

    def test_query_brief_applications_closed_at_date_for_two_week_brief(self):
        with self.app.app_context():
            new_brief = Brief(data={'requirementsLength': '2 weeks'}, framework=self.framework, lot=self.lot)
            db.session.add(new_brief)
            db.session.commit()
            new_brief.published_at = datetime(2016, 3, 3, 12, 30, 1, 2)
            db.session.add(new_brief)
            db.session.commit()
            assert Brief.query.filter(Brief.applications_closed_at == naive_datetime(2016, 3, 17, 7, 0, 0)).count() == 1

    def test_query_brief_applications_closed_at_date_for_mix_of_brief_lengths(self):
        with self.app.app_context():
            briefA = Brief(data={'requirementsLength': '1 week'}, framework=self.framework, lot=self.lot)
            briefB = Brief(data={'requirementsLength': '2 weeks'}, framework=self.framework, lot=self.lot)
            briefC = Brief(data={}, framework=self.framework, lot=self.lot)
            db.session.add(briefA)
            db.session.add(briefB)
            db.session.add(briefC)
            db.session.commit()
            briefA.published_at = datetime(2016, 3, 10, 12, 30, 1, 2)
            briefB.published_at = datetime(2016, 3, 3, 12, 30, 1, 2)
            briefC.published_at = datetime(2016, 3, 3, 12, 30, 1, 2)
            db.session.add(briefA)
            db.session.add(briefB)
            db.session.add(briefC)
            db.session.commit()
            assert Brief.query.filter(Brief.applications_closed_at == naive_datetime(2016, 3, 17, 7, 0, 0)).count() == 3

    def test_expired_status_for_a_brief_with_passed_close_date(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot,
                          published_at=utcnow() - interval(days=1000))

            assert brief.status == 'closed'
            assert brief.clarification_questions_are_closed
            assert brief.applications_closed_at < utcnow()

    def test_can_set_draft_brief_to_the_same_status(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)
        brief.status = 'draft'

    def test_publishing_a_brief_sets_published_at(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot)
            assert brief.published_at is None

            brief.status = 'live'
            assert not brief.clarification_questions_are_closed
            assert isinstance(brief.published_at, builtindatetime)

    def test_withdrawing_a_brief_sets_withdrawn_at(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=utcnow())
            assert brief.withdrawn_at is None

            brief.status = 'withdrawn'
            assert isinstance(brief.withdrawn_at, builtindatetime)

    def test_status_must_be_valid(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)

        with pytest.raises(ValidationError):
            brief.status = 'invalid'

    def test_cannot_set_live_brief_to_invalid_closings(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=utcnow())

            with pytest.raises(ValidationError):
                brief.closed_at = utcnow() + pendulum.interval(days=999)

            with pytest.raises(ValidationError):
                brief.closed_at = utcnow() - pendulum.interval(days=10)

            with pytest.raises(ValidationError):
                brief.closed_at = utcnow() + pendulum.interval(days=5)

            brief.closed_at = utcnow() + pendulum.interval(days=10)

            with pytest.raises(ValidationError):
                brief.questions_closed_at = utcnow() + pendulum.interval(days=20)

    def test_cannot_set_live_brief_to_draft(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=utcnow())

            with pytest.raises(ValidationError):
                brief.status = 'draft'

    def test_can_set_live_brief_to_withdrawn(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=utcnow())
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
        with self.app.app_context():
            brief = Brief(
                data={}, framework=self.framework, lot=self.lot,
                published_at=utcnow() - interval(days=1), withdrawn_at=utcnow()
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
        self.framework.status = 'pending'
        brief = Brief(
            data={},
            framework=self.framework,
            lot=self.lot
        )
        with pytest.raises(ValidationError) as e:
            brief.copy()

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
            assert isinstance(brief_response.created_at, builtindatetime)
            assert brief_response.data == {}

    def test_create_a_new_brief_response_with_data(self):
        ERSPEC = {'essentialRequirements': ['be cool', 'be rad']}
        FIELDS = {'essentialRequirements': ['i am cool', 'i am rad']}

        with self.app.app_context():
            self.brief.data = ERSPEC
            db.session.add(self.brief)
            db.session.commit()
            brief_response = BriefResponse(data=FIELDS, brief=self.brief, supplier=self.supplier)

            db.session.add(brief_response)
            db.session.commit()

            try:
                brief_response.validate()
            except ValidationError as v:
                errors = v.message
                assert 'essentialRequirements' not in errors

            assert brief_response.id is not None
            assert brief_response.supplier_code == 0
            assert brief_response.brief_id == self.brief.id
            assert isinstance(brief_response.created_at, builtindatetime)
            assert brief_response.data == FIELDS

    def test_create_a_brief_with_comments(self):
        with self.app.app_context():
            brief_response = BriefResponse(data={}, brief=self.brief, supplier=self.supplier)
            db.session.add(brief_response)
            db.session.commit()

            assert brief_response.id is not None
            assert brief_response.supplier_code == 0
            assert brief_response.brief_id == self.brief.id
            assert isinstance(brief_response.created_at, builtindatetime)
            assert brief_response.data == {}

    def test_whitespace_is_stripped_from_brief_response_answer(self):
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
                    'status': 'draft',
                    'createdAt': mock.ANY,
                    'submittedAt': mock.ANY,
                    'updatedAt': mock.ANY,
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
            user = User(
                email_address='email@digital.gov.au',
                name='name',
                role='buyer',
                password='password',
                active=True,
                failed_login_count=0,
                created_at=utcnow(),
                updated_at=utcnow(),
                password_changed_at=utcnow()
            )
            db.session.add(user)
            db.session.commit()

            question = BriefClarificationQuestion(
                brief=self.brief, question="Why?", answer="Because", user_id=user.id)

            db.session.add(question)
            db.session.commit()

            assert isinstance(question.published_at, builtindatetime)

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

        assert e.value.message['question'] == 'under_word_limit'

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

        assert e.value.message['answer'] == 'under_word_limit'

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
        now = pendulum.now('UTC')
        later = now.add(hours=1)

        with self.app.app_context():
            with pendulum.test(now):

                self.setup_dummy_suppliers(1)
                self.setup_dummy_service(
                    service_id='1000000000',
                    supplier_code=0,
                    status='published',
                    framework_id=2)

                service = Service.query.filter(Service.service_id == '1000000000').first()

                assert service.updated_at == now
                assert service.created_at == now

            with pendulum.test(later):
                assert service.updated_at == now
                service.update_from_json({'foo': 'bar'})
                db.session.flush()
                assert service.updated_at == later

                db.session.add(service)
                assert service.created_at == now
                db.session.commit()

                assert service.created_at == now
                assert service.updated_at == later
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


class TestWorkOrder(BaseApplicationTest):
    def setup(self):
        super(TestWorkOrder, self).setup()
        with self.app.app_context():
            framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
            lot = framework.get_lot('digital-outcomes')
            self.brief = Brief(data={}, framework=framework, lot=lot)
            db.session.add(self.brief)
            db.session.commit()

            self.setup_dummy_suppliers(1)
            self.supplier = Supplier.query.filter(Supplier.code == 0).first()

    def test_create_a_new_work_order(self):
        with self.app.app_context():
            work_order = WorkOrder(data={}, brief=self.brief, supplier=self.supplier)
            db.session.add(work_order)
            db.session.commit()

            assert work_order.id is not None
            assert work_order.supplier_code == 0
            assert work_order.brief_id == self.brief.id
            assert isinstance(work_order.created_at, builtindatetime)
            assert work_order.data == {}

    def test_foreign_fields_are_removed_from_work_order_data(self):
        work_order = WorkOrder(data={})
        work_order.data = {'foo': 'bar', 'briefId': 5, 'supplierCode': 100}

        assert work_order.data == {'foo': 'bar'}

    def test_nulls_are_removed_from_work_order_data(self):
        work_order = WorkOrder(data={})
        work_order.data = {'foo': 'bar', 'bar': None}

        assert work_order.data == {'foo': 'bar'}

    def test_whitespace_is_stripped_from_work_order_data(self):
        work_order = WorkOrder(data={})
        work_order.data = {'foo': ' bar ', 'bar': ['', '  foo']}

        assert work_order.data == {'foo': 'bar', 'bar': ['foo']}

    def test_work_order_can_be_serialized(self):
        with self.app.app_context():
            work_order = WorkOrder(data={'foo': 'bar'}, brief=self.brief, supplier=self.supplier)
            db.session.add(work_order)
            db.session.commit()

            with mock.patch('app.models.url_for') as url_for:
                url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
                assert work_order.serialize() == {
                    'id': work_order.id,
                    'briefId': self.brief.id,
                    'supplierCode': 0,
                    'supplierName': 'Supplier 0',
                    'createdAt': mock.ANY,
                    'foo': 'bar',
                    'links': {
                        'self': (('.get_work_order',), {'work_order_id': work_order.id}),
                        'brief': (('.get_brief',), {'brief_id': self.brief.id}),
                        'supplier': (('.get_supplier',), {'code': 0}),
                    }
                }


class TestApplication(BaseApplicationTest):
    def setup(self):
        super(TestApplication, self).setup()

    @pytest.fixture()
    def app(self):
        app = create_app('test')
        app.config['SERVER_NAME'] = 'localhost'
        app.config['CSRF_ENABLED'] = False
        yield app

    @pytest.fixture()
    def supplier(self, app):
        self.setup()
        with app.app_context():
            self.setup_dummy_suppliers(1)
            db.session.commit()
            supplier = (
                db.session
                  .query(Supplier)
                  .filter(Supplier.code == 0)
                  .first()
            )

            yield supplier

    @pytest.fixture()
    def new_application(self, app):
        with app.app_context():
            application = Application(data=INCOMING_APPLICATION_DATA)
            db.session.add(application)
            db.session.commit()
            yield application

    @pytest.fixture()
    def existing_application(self, app, supplier):
        with app.app_context():
            application = Application(data=INCOMING_APPLICATION_DATA, supplier=supplier)
            db.session.add(application)
            db.session.commit()
            yield application

    @pytest.fixture()
    def applicant(self, app, new_application):
        with app.app_context():
            applicant = User(
                email_address='email@digital.gov.au',
                name='name',
                role='applicant',
                password='password',
                active=True,
                failed_login_count=0,
                created_at=utcnow(),
                updated_at=utcnow(),
                password_changed_at=utcnow(),
                application=new_application
            )

            db.session.add(applicant)
            db.session.commit()
            yield applicant

    @pytest.fixture()
    def supplier_user(self, app, existing_application, supplier):
        with app.app_context():
            user = User(
                email_address='email@digital.gov.au',
                name='name',
                role='supplier',
                password='password',
                active=True,
                failed_login_count=0,
                created_at=utcnow(),
                updated_at=utcnow(),
                password_changed_at=utcnow(),
                application=existing_application,
                supplier=supplier
            )

            db.session.add(user)
            db.session.commit()
            yield user

    @mock.patch('app.jiraapi.JIRA')
    @pytest.mark.parametrize('test_data', [
        {
            'labourHire': {
                'qld': {'expiry': ''},
                'act': {'expiry': '', 'licenceNumber': ''},
                'vic': {'licenceNumber': ''}
            }
        },
        {
            'labourHire': {
                'qld': {'expiry': None},
                'act': {'expiry': None, 'licenceNumber': None},
                'vic': {'licenceNumber': None}
            }
        }
    ])
    def test_labour_hire_data_is_removed_for_new_seller_application(self, jira, app, new_application,
                                                                    applicant, test_data):
        with app.app_context():
            new_application.data['labourHire'] = test_data['labourHire']

            assert new_application.status == 'saved'
            new_application.submit_for_approval()
            assert new_application.status == 'submitted'
            new_application.set_approval(approved=True)
            assert new_application.status == 'approved'

            labour_hire = new_application.data.get('labourHire')
            assert labour_hire == {}

            supplier = new_application.supplier
            supplier_labour_hire = supplier.data.get('labourHire')
            assert supplier_labour_hire == {}

    @mock.patch('app.jiraapi.JIRA')
    @pytest.mark.parametrize('test_data', [
        {
            'labourHire': {
                'qld': {'expiry': ''},
                'act': {'expiry': '', 'licenceNumber': ''},
                'vic': {'licenceNumber': ''}
            }
        },
        {
            'labourHire': {
                'qld': {'expiry': None},
                'act': {'expiry': None, 'licenceNumber': None},
                'vic': {'licenceNumber': None}
            }
        }
    ])
    def test_labour_hire_data_is_removed_for_existing_seller_application(self, jira, app, existing_application,
                                                                         supplier_user, test_data):
        with app.app_context():
            existing_application.data['labourHire'] = test_data['labourHire']

            assert existing_application.status == 'saved'
            existing_application.submit_for_approval()
            assert existing_application.status == 'submitted'
            existing_application.set_approval(approved=True)
            assert existing_application.status == 'approved'

            labour_hire = existing_application.data.get('labourHire')
            assert labour_hire == {}

            supplier = existing_application.supplier
            supplier_labour_hire = supplier.data.get('labourHire')
            assert supplier_labour_hire == {}

    @mock.patch('app.jiraapi.JIRA')
    @pytest.mark.parametrize('test_data', [
        {
            'labourHire': {
                'qld': {'expiry': ''},
                'act': {'expiry': '2040-10-22', 'licenceNumber': '123'},
                'vic': {'licenceNumber': ''}
            }
        }
    ])
    def test_labour_hire_data_is_retained_for_new_seller_application(self, jira, app, new_application,
                                                                     applicant, test_data):
        with app.app_context():
            new_application.data['labourHire'] = test_data['labourHire']

            assert new_application.status == 'saved'
            new_application.submit_for_approval()
            assert new_application.status == 'submitted'
            new_application.set_approval(approved=True)
            assert new_application.status == 'approved'

            expected = {
                'act': {
                    'expiry': '2040-10-22',
                    'licenceNumber': '123'
                }
            }

            labour_hire = new_application.data.get('labourHire')
            assert labour_hire == expected

            supplier = new_application.supplier
            supplier_labour_hire = supplier.data.get('labourHire')
            assert supplier_labour_hire == expected

    @mock.patch('app.jiraapi.JIRA')
    @pytest.mark.parametrize('test_data', [
        {
            'labourHire': {
                'qld': {'expiry': ''},
                'act': {'expiry': '2040-10-22', 'licenceNumber': '123'},
                'vic': {'licenceNumber': ''}
            }
        }
    ])
    def test_labour_hire_data_is_retained_for_existing_seller_application(self, jira, app, existing_application,
                                                                          supplier_user, test_data):
        with app.app_context():
            existing_application.data['labourHire'] = test_data['labourHire']

            assert existing_application.status == 'saved'
            existing_application.submit_for_approval()
            assert existing_application.status == 'submitted'
            existing_application.set_approval(approved=True)
            assert existing_application.status == 'approved'

            expected = {
                'act': {
                    'expiry': '2040-10-22',
                    'licenceNumber': '123'
                }
            }

            labour_hire = existing_application.data.get('labourHire')
            assert labour_hire == expected

            supplier = existing_application.supplier
            supplier_labour_hire = supplier.data.get('labourHire')
            assert supplier_labour_hire == expected

    @mock.patch('app.jiraapi.JIRA')
    def test_new_seller_application(self, jira, app):
        with app.test_request_context('/hello'):
            application = Application(data=INCOMING_APPLICATION_DATA)
            user = User(
                email_address='email@digital.gov.au',
                name='name',
                role='applicant',
                password='password',
                active=True,
                failed_login_count=0,
                created_at=utcnow(),
                updated_at=utcnow(),
                password_changed_at=utcnow(),
                application=application
            )

            # flushing to database in order to set defaults (very annoying "feature" of sqlalchemy)
            db.session.add(application)
            db.session.add(user)
            db.session.flush()

            x_from_manual = application.serialize()
            x_from_deterministic = json.loads(application.json)

            subset = {
                k: v for k, v
                in x_from_deterministic.items()
                if k in x_from_manual
            }
            assert subset == x_from_manual

            assert application.status == 'saved'

            application.submit_for_approval()

            assert application.status == 'submitted'
            assert application.supplier is None

            with raises(ValidationError):
                application.submit_for_approval()

            application.set_approval(approved=False)

            assert application.status == 'approval_rejected'

            application.unreject_approval()
            assert application.status == 'submitted'

            application.set_approval(approved=True)

            with raises(ValidationError):
                application.set_approval(True)

            assert application.status == 'approved'
            assert application.supplier.status == 'limited'

            assert application.supplier.id is not None
            assert application.supplier.code is not None
            assert user.role == 'supplier'
            assert user.supplier_code == application.supplier.code

            db.session.flush()

            assert len(application.supplier.contacts) == 1

    @mock.patch('app.jiraapi.JIRA')
    def test_existing_seller_application(self, jira, app, supplier):
        with app.test_request_context('/hello'):
            application = Application(data=INCOMING_APPLICATION_DATA, supplier=supplier)
            user = User(
                email_address='email@digital.gov.au',
                name='name',
                role='supplier',
                password='password',
                active=True,
                failed_login_count=0,
                created_at=utcnow(),
                updated_at=utcnow(),
                password_changed_at=utcnow(),
                application=application,
                supplier=supplier
            )

            db.session.add(application)
            db.session.add(user)
            db.session.flush()

            new_data = INCOMING_APPLICATION_DATA
            new_data['summary'] = 'New Summary'

            # use this application to do an existing seller update
            application.data = new_data
            application.status = 'submitted'

            db.session.flush()

            application.set_approval(True)

            # check that the update took place
            assert application.supplier.summary == 'New Summary'

            # make sure this didn't change
            assert application.supplier.status == 'complete'

            # test application-from-existing-seller scenario

            supplier = application.supplier

            db.session.delete(application)
            db.session.flush()

            app_from_existing = Application()
            app_from_existing.update_from_json(supplier.json)

            db.session.add(app_from_existing)
            db.session.flush()
            db.session.refresh(app_from_existing)

            assert app_from_existing.supplier_code == supplier.code
            assert app_from_existing.supplier.code == supplier.code
            assert app_from_existing.supplier == supplier

    def test_application_and_supplier_domains(self, app, supplier):
        with app.test_request_context('/hello'):
            supp = supplier
            db.session.add(supp)

            supp.update_from_json(
                {"prices": [{
                    "serviceRole": {"category": "Business Analysis", "role": "Junior Business Analyst"},
                    "hourlyRate": "1.10",
                    "dailyRate": "2.90"}]}
            )

            db.session.commit()

            assert supp.assessed_domains == []
            assert supp.unassessed_domains == []

            supp.add_unassessed_domain('Change, Training and Transformation')

            assert supp.assessed_domains == []
            assert supp.unassessed_domains == ['Change, Training and Transformation']

            supp.update_domain_assessment_status('Change, Training and Transformation', 'assessed')

            assert supp.assessed_domains == [
                'Change, Training and Transformation'
            ]

            assert supp.unassessed_domains == []

            with raises(DataError):
                supp.update_domain_assessment_status('Change, Training and Transformation', 'bad_status_value')

    def test_signed_agreement(self, app):
        with app.test_request_context('/hello'):
            application = Application(data=INCOMING_APPLICATION_DATA)
            user = User(
                email_address='email@digital.gov.au',
                name='name',
                role='applicant',
                password='password',
                active=True,
                failed_login_count=0,
                created_at=utcnow(),
                updated_at=utcnow(),
                password_changed_at=utcnow(),
                application=application
            )

            now = pendulum.now('utc')
            agreement = MasterAgreement(
                start_date=now.subtract(years=1),
                end_date=now.add(years=1),
                data={
                    'htmlUrl': '/path/to/agreement.html',
                    'pdfUrl': '/path/to/agreement.pdf'
                }
            )

            # flushing to database in order to set defaults (very annoying "feature" of sqlalchemy)
            db.session.add(application)
            db.session.add(user)
            db.session.add(agreement)
            db.session.flush()

            assert len(application.serializable['signed_agreements']) == 0

            signed_agreement = SignedAgreement(
                agreement_id=agreement.id,
                user_id=user.id,
                application_id=application.id,
                signed_at=now
            )
            db.session.add(signed_agreement)
            db.session.flush()

            assert application.serializable['signed_agreements'][0] == {
                'htmlUrl': '/path/to/agreement.html',
                'pdfUrl': '/path/to/agreement.pdf',
                'signedAt': now,
                'user': {
                    'emailAddress': 'email@digital.gov.au',
                    'name': 'name'
                }
            }


class TestSuppliers(BaseApplicationTest):
    def setup(self):
        super(TestSuppliers, self).setup()

    @pytest.fixture()
    def supplier(self):
        self.setup()
        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            supplier = Supplier.query.first()
            supplier.is_recruiter = True

            recruiter_info = RecruiterInfo(
                id=1, active_candidates=12, database_size=34, placed_candidates=56, margin='10%', markup='10%'
            )

            db.session.add(recruiter_info)
            supplier_domain = SupplierDomain(
                supplier=supplier,
                domain=Domain.get_by_name_or_id('Data science'),
                status='unassessed',
                recruiter_info=recruiter_info
            )

            db.session.add(supplier_domain)
            db.session.commit()
            yield supplier

    def test_recruiter_info_is_deleted_when_domain_is_removed(self, supplier):
        supplier.remove_domain('Data science')
        supplier_domain = SupplierDomain.query.first()
        recruiter_info = RecruiterInfo.query.first()

        assert supplier_domain is None
        assert recruiter_info is None
        assert len(supplier.domains) == 0
