from datetime import datetime, timedelta

import mock
import pytest
from freezegun import freeze_time
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import (
    User, Lot, Framework,
    Supplier, SupplierFramework, FrameworkAgreement,
    Brief, BriefResponse,
    ValidationError,
    BriefClarificationQuestion,
    ArchivedService, DraftService, Service,
    FrameworkLot,
    ContactInformation
)
from tests.bases import BaseApplicationTest
from tests.helpers import FixtureMixin

from dmtestutils.api_model_stubs import (
    ArchivedServiceStub,
    BriefStub,
    BriefResponseStub,
    DraftServiceStub,
    FrameworkStub,
    FrameworkAgreementStub,
    LotStub,
    ServiceStub,
    SupplierStub,
    SupplierFrameworkStub
)


class TestJSONFieldsAreMutable(BaseApplicationTest):

    def test_json_fields_are_mutable_and_updated(self):
        test_object = Lot(slug='test-lot', name='Test Lot', data={'test': 'data'})
        db.session.add(test_object)
        db.session.commit()

        assert Lot.query.get(test_object.id).data == {'test': 'data'}

        test_object.data['test'] = 'update'
        db.session.add(test_object)
        db.session.commit()

        assert Lot.query.get(test_object.id).data == {'test': 'update'}

    def test_json_fields_with_nested_data_are_mutable_and_updated(self):
        test_object = Lot(slug='test-lot', name='Test Lot', data={'test': {'with': {'nested': 'data'}}})
        db.session.add(test_object)
        db.session.commit()

        assert Lot.query.get(test_object.id).data == {'test': {'with': {'nested': 'data'}}}

        test_object.data['test']['with']['nested'] = 'update'
        db.session.add(test_object)
        db.session.commit()

        assert Lot.query.get(test_object.id).data == {'test': {'with': {'nested': 'update'}}}


class TestUser(BaseApplicationTest, FixtureMixin):
    def test_should_not_return_password_on_user(self):
        self.setup_default_buyer_domain()

        now = datetime.utcnow()
        user = User(
            email_address='email@digital.gov.uk',
            name='name',
            role='buyer',
            password='password',
            active=True,
            failed_login_count=0,
            created_at=now,
            updated_at=now,
            password_changed_at=now
        )

        serialized_user = user.serialize()
        assert serialized_user['emailAddress'] == "email@digital.gov.uk"
        assert serialized_user['name'] == "name"
        assert serialized_user['role'] == "buyer"
        assert 'password' not in serialized_user

    def test_should_fall_back_to_created_at_time_if_no_logged_in_at_timestamp(self):
        self.setup_default_buyer_domain()
        with freeze_time('2018-01-09'):
            then = datetime.utcnow()
            later = then + timedelta(weeks=3)
            user = User(
                email_address='email@digital.gov.uk',
                name='name',
                role='buyer',
                password='password',
                active=True,
                failed_login_count=0,
                created_at=then,
                updated_at=later,
                password_changed_at=later,
                logged_in_at=None
            )
        assert user.logged_in_at is None
        assert user.serialize()['loggedInAt'] == "2018-01-09T00:00:00.000000Z"

    def test_supplier_user_serializes_extra_supplier_fields(self):
        now = datetime.utcnow()
        supplier = Supplier(name="Joe Bananas", organisation_size="micro", supplier_id=1234)
        db.session.add(supplier)
        db.session.commit()
        user = User(
            email_address='supplier@example.com',
            name='name',
            role='supplier',
            password='password',
            active=True,
            failed_login_count=0,
            created_at=now,
            updated_at=now,
            password_changed_at=now,
        )
        user.supplier = supplier

        serialized_user = user.serialize()
        assert serialized_user['supplier']['supplierId'] == 1234
        assert serialized_user['supplier']['name'] == "Joe Bananas"
        assert serialized_user['supplier']['organisationSize'] == "micro"

    def test_buyer_user_requires_valid_email_domain(self):
        with pytest.raises(ValidationError) as exc:
            self.setup_default_buyer_domain()
            valid_buyer_user = User(
                email_address='email@digital.gov.uk',
                name='name',
                role='buyer',
                password='password',
                active=True,
            )
            # Changing email to invalid domain raises an error
            valid_buyer_user.email_address = 'email@nope.org'

        assert str(exc.value) == 'invalid_buyer_domain'

    @pytest.mark.parametrize('role', User.ADMIN_ROLES)
    def test_admin_user_requires_whitelisted_email_domain(self, role):
        with pytest.raises(ValidationError) as exc:
            valid_admin_user = User(
                email_address='email@digital.cabinet-office.gov.uk',
                name='name',
                role=role,
                password='password',
                active=True,
            )
            # Changing email to invalid domain raises an error
            valid_admin_user.email_address = 'email@nope.org'
        assert str(exc.value) == 'invalid_admin_domain'

    def test_user_with_invalid_email_domain_cannot_be_changed_to_buyer_role(self):
        with pytest.raises(ValidationError) as exc:
            self.setup_default_buyer_domain()
            valid_admin_user = User(
                email_address='email@crowncommercial.gov.uk',
                name='name',
                role='admin',
                password='password',
                active=True,
            )
            # Changing role to buyer raises an error
            valid_admin_user.role = 'buyer'

        assert str(exc.value) == 'invalid_buyer_domain'

    @pytest.mark.parametrize('role', User.ADMIN_ROLES)
    def test_user_with_invalid_email_domain_cannot_be_changed_to_admin_role(self, role):
        with pytest.raises(ValidationError) as exc:
            self.setup_default_buyer_domain()
            valid_buyer_user = User(
                email_address='email@digital.gov.uk',
                name='name',
                role='buyer',
                password='password',
                active=True,
            )
            # Changing role to admin raises an error
            valid_buyer_user.role = role
        assert str(exc.value) == 'invalid_admin_domain'

    @pytest.mark.parametrize('role', User.ROLES)
    def test_remove_personal_data_should_set_personal_data_removed_flag(self, role):
        self.default_buyer_domain = "digital.cabinet-office.gov.uk"
        self.setup_default_buyer_domain()
        self.default_buyer_domain = "user.marketplace.team"
        self.setup_default_buyer_domain()
        now = datetime.utcnow()
        user = User(
            email_address='email@digital.cabinet-office.gov.uk',
            name='name',
            phone_number='555-555-555',
            role=role,
            password='password',
            active=True,
            failed_login_count=0,
            created_at=now,
            updated_at=now,
            password_changed_at=now,
        )

        db.session.add(user)
        db.session.commit()
        user.remove_personal_data()
        db.session.add(user)
        db.session.commit()

        assert user.personal_data_removed is True

    @pytest.mark.parametrize('role', set(User.ROLES) - {'supplier'})
    @mock.patch('app.models.main.uuid4', return_value='111')
    @mock.patch('app.encryption.generate_password_hash', return_value=b'222')
    def test_remove_personal_data_should_remove_personal_data(self, generate_password_hash, uuid4, role):
        self.default_buyer_domain = "digital.cabinet-office.gov.uk"
        self.setup_default_buyer_domain()
        self.default_buyer_domain = "user.marketplace.team"
        self.setup_default_buyer_domain()
        now = datetime.utcnow()
        user = User(
            email_address='email@digital.cabinet-office.gov.uk',
            name='name',
            phone_number='555-555-555',
            role=role,
            password='password',
            active=True,
            failed_login_count=0,
            created_at=now,
            updated_at=now,
            password_changed_at=now,
        )

        db.session.add(user)
        db.session.commit()
        user.remove_personal_data()
        db.session.add(user)
        db.session.commit()

        assert user.active is False
        assert user.name == '<removed>'
        assert user.phone_number == '<removed>'
        if role == "buyer":
            assert user.email_address == "<removed><111>@user.marketplace.team"
        else:
            assert user.email_address == "<removed><111>@digital.cabinet-office.gov.uk"
        assert user.user_research_opted_in is False
        assert user.password == '222'

        generate_password_hash.assert_called_once_with('111', 10)
        assert uuid4.call_count == 2

    @mock.patch('app.models.main.uuid4', return_value='111')
    @mock.patch('app.encryption.generate_password_hash', return_value=b'222')
    def test_supplier_personal_data_removal(self, generate_password_hash, uuid4):
        now = datetime.utcnow()
        user = User(
            email_address='email@digital.cabinet-office.gov.uk',
            name='name',
            phone_number='555-555-555',
            role='supplier',
            password='password',
            active=True,
            failed_login_count=0,
            created_at=now,
            updated_at=now,
            password_changed_at=now,
        )
        db.session.add(user)
        db.session.commit()
        user.remove_personal_data()
        db.session.add(user)
        db.session.commit()

        assert user.email_address == '<removed>@111.com'

        assert user.active is False
        assert user.name == '<removed>'
        assert user.phone_number == '<removed>'
        assert user.user_research_opted_in is False
        assert user.password == '222'

        generate_password_hash.assert_called_once_with('111', 10)
        assert uuid4.call_count == 2

    @pytest.mark.parametrize('role', set(User.ROLES))
    def test_cannot_change_once_personal_data_removed(self, role):
        self.default_buyer_domain = "digital.cabinet-office.gov.uk"
        self.setup_default_buyer_domain()
        self.default_buyer_domain = "user.marketplace.team"
        self.setup_default_buyer_domain()
        now = datetime.utcnow()
        user = User(
            email_address='email@digital.cabinet-office.gov.uk',
            name='name',
            phone_number='555-555-555',
            role=role,
            password='password',
            active=True,
            failed_login_count=0,
            created_at=now,
            updated_at=now,
            password_changed_at=now,
        )
        db.session.add(user)
        db.session.commit()

        user.remove_personal_data()

        db.session.add(user)
        db.session.commit()

        with pytest.raises(ValidationError) as e:
            user = User.query.filter(User.id == user.id).first()
            user.name = 'We are not allowed to update a user whose personal data has been removed'
            db.session.add(user)
            db.session.commit()

        assert str(e.value) == 'Cannot update an object once personal data has been removed'


class TestContactInformation(BaseApplicationTest):

    def setup(self):
        super(TestContactInformation, self).setup()
        self.supplier = Supplier(name="Test Supplier", organisation_size="micro", supplier_id=11111)
        self.contact_information = ContactInformation(
            supplier_id=11111,
            contact_name='Test Name',
            phone_number='Test Number',
            email='test.email@example.com',
            address1='Test address line 1',
            city='Test city',
            postcode='T3S P05C0'
        )
        db.session.add_all([self.supplier, self.contact_information])

    @mock.patch('app.models.main.uuid4', return_value='111')
    def test_remove_personal_data(self, uuid_mock):
        self.contact_information.remove_personal_data()
        db.session.add(self.contact_information)
        db.session.commit()

        assert self.contact_information.personal_data_removed
        assert self.contact_information.contact_name == '<removed>'
        assert self.contact_information.phone_number == '<removed>'
        assert self.contact_information.email == '<removed>@111.com'
        assert self.contact_information.address1 == '<removed>'
        assert self.contact_information.city == '<removed>'
        assert self.contact_information.postcode == '<removed>'

    def test_update_from_json_resets_remove_personal_data_flag(self):
        """If we are using the update_from_json it is to introduce fields that should be wiped of personal data as per
        our retention policy. An update via this method means that we are introducing personal data and that the flag
        should be reset.
        """
        self.contact_information.remove_personal_data()
        db.session.add(self.contact_information)
        db.session.commit()

        self.contact_information.update_from_json({
            'contactName': 'New Test Name',
            'phoneNumber': 'New Test Number',
            'email': 'new.test.email@example.com',
            'address1': 'New Test address line 1',
            'city': 'New Test City',
            'postcode': 'T3S P05C0',
        })
        db.session.add(self.contact_information)
        db.session.commit()

        assert not self.contact_information.personal_data_removed
        assert self.contact_information.phone_number == 'New Test Number'

    def test_can_change_object_once_personal_data_removed(self):
        self.contact_information.remove_personal_data()
        db.session.add(self.contact_information)
        db.session.commit()

        self.contact_information.contact_name = 'Can change this value'
        db.session.add(self.contact_information)
        db.session.commit()

        assert (
            ContactInformation.query.filter(ContactInformation.id == self.contact_information.id).first().contact_name
            == 'Can change this value'
        )


class TestFrameworks(BaseApplicationTest):

    def test_framework_should_not_accept_invalid_status(self):
        with pytest.raises(ValidationError):
            f = Framework(
                name='foo',
                slug='foo',
                framework='g-cloud',
                status='invalid',
                has_direct_award=True,
                has_further_competition=False,
            )
            db.session.add(f)
            db.session.commit()

    def test_framework_should_accept_valid_statuses(self):
        for i, status in enumerate(Framework.STATUSES):
            f = Framework(
                name='foo',
                slug='foo-{}'.format(i),
                framework='g-cloud',
                status=status,
                has_direct_award=True,
                has_further_competition=False,
            )
            db.session.add(f)
            db.session.commit()

    def test_framework_serialization(self):
        f = Framework(
            id=109,
            name='foo',
            slug='foo-109',
            framework='g-cloud',
            status='open',
            applications_close_at_utc=datetime(2000, 1, 1),
            intention_to_award_at_utc=datetime(2000, 2, 2),
            clarifications_close_at_utc=datetime(2000, 3, 3),
            clarifications_publish_at_utc=datetime(2000, 4, 4),
            framework_live_at_utc=datetime(2000, 5, 5),
            framework_expires_at_utc=datetime(2000, 6, 6),
            has_direct_award=True,
            has_further_competition=False,
        )
        db.session.add(f)
        db.session.commit()

        assert f.serialize() == {
            'id': 109,
            'name': 'foo',
            'slug': 'foo-109',
            'framework': 'g-cloud',
            'family': 'g-cloud',
            'status': 'open',
            'clarificationQuestionsOpen': False,
            'lots': [],
            'applicationsCloseAtUTC': '2000-01-01T00:00:00.000000Z',
            'intentionToAwardAtUTC': '2000-02-02T00:00:00.000000Z',
            'clarificationsCloseAtUTC': '2000-03-03T00:00:00.000000Z',
            'clarificationsPublishAtUTC': '2000-04-04T00:00:00.000000Z',
            'frameworkLiveAtUTC': '2000-05-05T00:00:00.000000Z',
            'frameworkExpiresAtUTC': '2000-06-06T00:00:00.000000Z',
            'allowDeclarationReuse': False,
            'frameworkAgreementDetails': {},
            'countersignerName': None,
            'frameworkAgreementVersion': None,
            'variations': {},
            'hasDirectAward': True,
            'hasFurtherCompetition': False,
            'isESignatureSupported': True
        }

    def test_framework_serialization_with_default_datetimes(self):
        f = Framework(
            id=109,
            name='foo',
            slug='foo-109',
            framework='g-cloud',
            status='open',
            has_direct_award=True,
            has_further_competition=False,
        )
        db.session.add(f)
        db.session.commit()

        assert f.serialize() == {
            'id': 109,
            'name': 'foo',
            'slug': 'foo-109',
            'framework': 'g-cloud',
            'family': 'g-cloud',
            'status': 'open',
            'clarificationQuestionsOpen': False,
            'lots': [],
            'applicationsCloseAtUTC': '1970-01-01T00:00:00.000000Z',
            'intentionToAwardAtUTC': '1970-01-01T00:00:00.000000Z',
            'clarificationsCloseAtUTC': '1970-01-01T00:00:00.000000Z',
            'clarificationsPublishAtUTC': '1970-01-01T00:00:00.000000Z',
            'frameworkLiveAtUTC': '1970-01-01T00:00:00.000000Z',
            'frameworkExpiresAtUTC': '1970-01-01T00:00:00.000000Z',
            'allowDeclarationReuse': False,
            'frameworkAgreementDetails': {},
            'countersignerName': None,
            'frameworkAgreementVersion': None,
            'variations': {},
            'hasDirectAward': True,
            'hasFurtherCompetition': False,
            'isESignatureSupported': True
        }

    def test_framework_serialize_keys_match_api_stub_keys(self):
        # Ensures our dmtestutils.api_model_stubs are kept up to date
        framework = Framework(
            id=109,
            name='foo',
            slug='foo-109',
            framework='g-cloud',
            has_direct_award=True,
            has_further_competition=False
        )
        db.session.add(framework)
        db.session.commit()

        framework_stub = FrameworkStub()
        assert sorted(framework.serialize().keys()) == sorted(framework_stub.response().keys())

    @pytest.mark.parametrize("slug,is_esignature_supported", [
        ('g-cloud-11', False),
        ('g-cloud-10', False),
        ('g-cloud-9', False),
        ('g-cloud-8', False),
        ('g-cloud-7', False),
        ('g-cloud-6', False),
        ('g-cloud-5', False),
        ('g-cloud-4', False),
        ('g-cloud-12', True),
        ('g-cloud-100', True),
        ('digital-outcomes-and-specialists', False),
        ('digital-outcomes-and-specialists-2', False),
        ('digital-outcomes-and-specialists-3', False),
        ('digital-outcomes-and-specialists-4', False),
        ('digital-outcomes-and-specialists-5', True),
        ('digital-outcomes-and-specialists-100', True),
    ])
    def test_framework_esignature_supported(self, slug, is_esignature_supported):
        framework = Framework(
            id=109,
            name='foo',
            slug=slug,
            framework='g-cloud',
            has_direct_award=True,
            has_further_competition=False
        )

        assert framework.is_esignature_supported == is_esignature_supported


class TestBriefs(BaseApplicationTest, FixtureMixin):
    def setup(self):
        super(TestBriefs, self).setup()
        self.framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
        self.lot = self.framework.get_lot('digital-outcomes')

    def test_create_a_new_brief(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)
        db.session.add(brief)
        db.session.commit()

        assert isinstance(brief.created_at, datetime)
        assert isinstance(brief.updated_at, datetime)
        assert brief.id is not None
        assert brief.data == dict()
        assert brief.is_a_copy is False

    def test_updating_a_brief_updates_dates(self):
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

    def test_buyer_users_can_be_added_to_a_brief(self):
        self.setup_dummy_user(role='buyer')

        brief = Brief(data={}, framework=self.framework, lot=self.lot,
                      users=User.query.all())

        assert len(brief.users) == 1

    def test_non_buyer_users_cannot_be_added_to_a_brief(self):
        self.setup_dummy_user(role='admin')

        with pytest.raises(ValidationError):
            Brief(data={}, framework=self.framework, lot=self.lot,
                  users=User.query.all())

    def test_brief_lot_must_be_associated_to_the_framework(self):
        other_framework = Framework.query.filter(Framework.slug == 'g-cloud-7').first()

        brief = Brief(data={}, framework=other_framework, lot=self.lot)
        db.session.add(brief)
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_brief_lot_must_require_briefs(self):
        with pytest.raises(ValidationError):
            Brief(data={},
                  framework=self.framework,
                  lot=self.framework.get_lot('user-research-studios'))

    def test_cannot_update_lot_by_id(self):
        with pytest.raises(ValidationError):
            Brief(data={},
                  framework=self.framework,
                  lot_id=self.framework.get_lot('user-research-studios').id)

    def test_add_brief_clarification_question(self):
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
        brief = Brief(data={}, framework=self.framework, lot=self.lot, status="live")
        db.session.add(brief)
        brief.add_clarification_question("How?", "This")
        brief.add_clarification_question("When", "Then")
        db.session.commit()

        assert brief.clarification_questions[0].question == "How?"
        assert brief.clarification_questions[1].question == "When"

    def test_brief_serialize_keys_match_api_stub_keys(self):
        # Ensures our dmtestutils.api_model_stubs are kept up to date
        brief = Brief(
            data={"title": "something"}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1)
        )
        # Commit the Brief so we get an id
        db.session.add(brief)
        db.session.commit()

        brief_stub = BriefStub(
            framework_slug=self.framework.slug, status='open', lot=self.lot, clarification_questions_closed=True,
        )
        assert sorted(brief.serialize().keys()) == sorted(brief_stub.response().keys())
        assert (
            sorted(brief.serialize(with_users=True, with_clarification_questions=True).keys()) ==
            sorted(brief_stub.single_result_response()['briefs'].keys())
        )


class TestBriefStatuses(BaseApplicationTest, FixtureMixin):
    def setup(self):
        super(TestBriefStatuses, self).setup()
        self.framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
        self.lot = self.framework.get_lot('digital-outcomes')

    def test_status_defaults_to_draft(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)
        assert brief.status == 'draft'

    def test_live_status_for_briefs_with_published_at(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime.utcnow())
        assert brief.status == 'live'

    def test_closed_status_for_a_brief_with_passed_close_date(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot,
                      published_at=datetime.utcnow() - timedelta(days=1000))

        assert brief.status == 'closed'
        assert brief.clarification_questions_are_closed
        assert brief.applications_closed_at < datetime.utcnow()

    def test_awarded_status_for_a_brief_with_an_awarded_brief_response(self):
        self.setup_dummy_suppliers(1)
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1))
        brief_response = BriefResponse(brief=brief, supplier_id=0, submitted_at=datetime.utcnow(), data={})
        brief_response.award_details = {"confirmed": "details"}
        brief_response.awarded_at = datetime(2016, 12, 12, 1, 1, 1)
        db.session.add_all([brief, brief_response])
        db.session.commit()

        brief = Brief.query.get(brief.id)
        assert brief.status == 'awarded'

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

    def test_cancelling_a_brief_sets_cancelled_at(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1))
        assert brief.cancelled_at is None

        brief.status = 'cancelled'
        assert isinstance(brief.cancelled_at, datetime)

    def test_unsuccessfulling_a_brief_sets_unsuccessful_at(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1))
        assert brief.unsuccessful_at is None

        brief.status = 'unsuccessful'
        assert isinstance(brief.unsuccessful_at, datetime)

    def test_can_set_draft_brief_to_the_same_status(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)
        brief.status = 'draft'

    def test_can_set_live_brief_to_withdrawn(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime.utcnow())
        brief.status = 'withdrawn'

        assert brief.published_at is not None
        assert brief.withdrawn_at is not None

    def test_cannot_set_any_brief_to_an_invalid_status(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)

        with pytest.raises(ValidationError) as e:
            brief.status = 'invalid'
        assert e.value.message == "Cannot change brief status from 'draft' to 'invalid'"

    @pytest.mark.parametrize('status', ['draft', 'closed', 'awarded', 'cancelled', 'unsuccessful'])
    def test_cannot_set_live_brief_to_non_withdrawn_status(self, status):
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime.utcnow())

        with pytest.raises(ValidationError) as e:
            brief.status = status
        assert e.value.message == "Cannot change brief status from 'live' to '{}'".format(status)

    @pytest.mark.parametrize('status', ['withdrawn', 'closed', 'awarded', 'cancelled', 'unsuccessful'])
    def test_cannot_set_draft_brief_to_withdrawn_closed_awarded_cancelled_or_unsuccessful(self, status):
        brief = Brief(data={}, framework=self.framework, lot=self.lot)

        with pytest.raises(ValidationError) as e:
            brief.status = status
        assert e.value.message == "Cannot change brief status from 'draft' to '{}'".format(status)

    def test_cannot_change_status_of_withdrawn_brief(self):
        brief = Brief(
            data={}, framework=self.framework, lot=self.lot,
            published_at=datetime.utcnow() - timedelta(days=1), withdrawn_at=datetime.utcnow()
        )

        for status in ['draft', 'live', 'closed', 'awarded', 'cancelled', 'unsuccessful']:
            with pytest.raises(ValidationError) as e:
                brief.status = status
            assert e.value.message == "Cannot change brief status from 'withdrawn' to '{}'".format(status)

    def test_status_order_sorts_briefs_by_search_result_status_ordering(self):
        draft_brief = Brief(data={}, framework=self.framework, lot=self.lot)
        live_brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime.utcnow())
        withdrawn_brief = Brief(
            data={}, framework=self.framework, lot=self.lot,
            published_at=datetime.utcnow() - timedelta(days=1), withdrawn_at=datetime.utcnow()
        )
        closed_brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1))
        cancelled_brief = Brief(
            data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1),
            cancelled_at=datetime(2000, 2, 2)
        )
        unsuccessful_brief = Brief(
            data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1),
            unsuccessful_at=datetime(2000, 2, 2)
        )

        awarded_brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1))
        self.setup_dummy_suppliers(1)
        brief_response = BriefResponse(
            brief=awarded_brief, data={}, supplier_id=0, submitted_at=datetime(2000, 2, 1),
            award_details={'pending': True}
        )
        db.session.add_all([
            draft_brief, live_brief, withdrawn_brief, closed_brief, awarded_brief, brief_response,
            cancelled_brief, unsuccessful_brief
        ])
        db.session.commit()
        # award the BriefResponse
        brief_response.awarded_at = datetime(2001, 1, 1)
        db.session.add(brief_response)
        db.session.commit()

        expected_result = [
            live_brief.status, closed_brief.status, awarded_brief.status,
            cancelled_brief.status, unsuccessful_brief.status,
            draft_brief.status, withdrawn_brief.status
        ]
        query_result = [
            q.status for q in Brief.query.order_by(Brief.status_order, Brief.published_at.desc(), Brief.id)
        ]

        assert query_result == expected_result


class TestBriefQueries(BaseApplicationTest, FixtureMixin):
    def setup(self):
        super(TestBriefQueries, self).setup()
        self.framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
        self.lot = self.framework.get_lot('digital-outcomes')

    def test_query_draft_brief(self):
        db.session.add(Brief(data={}, framework=self.framework, lot=self.lot))
        db.session.commit()

        assert Brief.query.filter(Brief.status == 'draft').count() == 1
        assert Brief.query.filter(Brief.status == 'live').count() == 0
        assert Brief.query.filter(Brief.status == 'withdrawn').count() == 0
        assert Brief.query.filter(Brief.status == 'closed').count() == 0
        assert Brief.query.filter(Brief.status == 'awarded').count() == 0
        assert Brief.query.filter(Brief.status == 'cancelled').count() == 0
        assert Brief.query.filter(Brief.status == 'unsuccessful').count() == 0

        # Check python implementation gives same result as the sql implementation
        assert Brief.query.all()[0].status == 'draft'

    def test_query_live_brief(self):
        db.session.add(Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime.utcnow()))
        db.session.commit()

        assert Brief.query.filter(Brief.status == 'draft').count() == 0
        assert Brief.query.filter(Brief.status == 'live').count() == 1
        assert Brief.query.filter(Brief.status == 'withdrawn').count() == 0
        assert Brief.query.filter(Brief.status == 'closed').count() == 0
        assert Brief.query.filter(Brief.status == 'awarded').count() == 0
        assert Brief.query.filter(Brief.status == 'cancelled').count() == 0
        assert Brief.query.filter(Brief.status == 'unsuccessful').count() == 0

        # Check python implementation gives same result as the sql implementation
        assert Brief.query.all()[0].status == 'live'

    def test_query_withdrawn_brief(self):
        db.session.add(Brief(
            data={}, framework=self.framework, lot=self.lot,
            published_at=datetime.utcnow() - timedelta(days=1), withdrawn_at=datetime.utcnow()
        ))
        db.session.commit()

        assert Brief.query.filter(Brief.status == 'draft').count() == 0
        assert Brief.query.filter(Brief.status == 'live').count() == 0
        assert Brief.query.filter(Brief.status == 'withdrawn').count() == 1
        assert Brief.query.filter(Brief.status == 'closed').count() == 0
        assert Brief.query.filter(Brief.status == 'awarded').count() == 0
        assert Brief.query.filter(Brief.status == 'cancelled').count() == 0
        assert Brief.query.filter(Brief.status == 'unsuccessful').count() == 0

        # Check python implementation gives same result as the sql implementation
        assert Brief.query.all()[0].status == 'withdrawn'

    def test_query_closed_brief(self):
        db.session.add(Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1)))
        db.session.commit()

        assert Brief.query.filter(Brief.status == 'draft').count() == 0
        assert Brief.query.filter(Brief.status == 'live').count() == 0
        assert Brief.query.filter(Brief.status == 'withdrawn').count() == 0
        assert Brief.query.filter(Brief.status == 'closed').count() == 1
        assert Brief.query.filter(Brief.status == 'awarded').count() == 0
        assert Brief.query.filter(Brief.status == 'cancelled').count() == 0
        assert Brief.query.filter(Brief.status == 'unsuccessful').count() == 0

        # Check python implementation gives same result as the sql implementation
        assert Brief.query.all()[0].status == 'closed'

    def test_query_cancelled_brief(self):
        db.session.add(
            Brief(
                data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1),
                cancelled_at=datetime(2000, 2, 2)
            )
        )
        db.session.commit()

        assert Brief.query.filter(Brief.status == 'draft').count() == 0
        assert Brief.query.filter(Brief.status == 'live').count() == 0
        assert Brief.query.filter(Brief.status == 'withdrawn').count() == 0
        assert Brief.query.filter(Brief.status == 'closed').count() == 0
        assert Brief.query.filter(Brief.status == 'awarded').count() == 0
        assert Brief.query.filter(Brief.status == 'cancelled').count() == 1
        assert Brief.query.filter(Brief.status == 'unsuccessful').count() == 0

        # Check python implementation gives same result as the sql implementation
        assert Brief.query.all()[0].status == 'cancelled'

    def test_query_unsuccessful_brief(self):
        db.session.add(
            Brief(
                data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1),
                unsuccessful_at=datetime(2000, 2, 2)
            )
        )
        db.session.commit()

        assert Brief.query.filter(Brief.status == 'draft').count() == 0
        assert Brief.query.filter(Brief.status == 'live').count() == 0
        assert Brief.query.filter(Brief.status == 'withdrawn').count() == 0
        assert Brief.query.filter(Brief.status == 'closed').count() == 0
        assert Brief.query.filter(Brief.status == 'awarded').count() == 0
        assert Brief.query.filter(Brief.status == 'cancelled').count() == 0
        assert Brief.query.filter(Brief.status == 'unsuccessful').count() == 1

        # Check python implementation gives same result as the sql implementation
        assert Brief.query.all()[0].status == 'unsuccessful'

    def test_query_awarded_brief(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1))
        self.setup_dummy_suppliers(1)
        brief_response = BriefResponse(
            brief=brief, data={}, supplier_id=0, submitted_at=datetime(2000, 2, 1),
            award_details={'pending': True}
        )
        db.session.add_all([brief, brief_response])
        db.session.commit()
        # award the BriefResponse
        brief_response.awarded_at = datetime(2001, 1, 1)
        db.session.add(brief_response)
        db.session.commit()

        assert Brief.query.filter(Brief.status == 'awarded').count() == 1
        # Check python implementation gives same result as the sql implementation
        assert Brief.query.all()[0].status == 'awarded'

    def test_query_brief_applications_closed_at_date_for_brief_with_no_requirements_length(self):
        db.session.add(Brief(data={}, framework=self.framework, lot=self.lot,
                             published_at=datetime(2016, 3, 3, 12, 30, 1, 2)))
        db.session.commit()
        assert Brief.query.filter(Brief.applications_closed_at == datetime(2016, 3, 17, 23, 59, 59)).count() == 1

    def test_query_brief_applications_closed_at_date_for_one_week_brief(self):
        db.session.add(Brief(data={'requirementsLength': '1 week'}, framework=self.framework, lot=self.lot,
                             published_at=datetime(2016, 3, 3, 12, 30, 1, 2)))
        db.session.commit()
        assert Brief.query.filter(Brief.applications_closed_at == datetime(2016, 3, 10, 23, 59, 59)).count() == 1

    def test_query_brief_applications_closed_at_date_for_two_week_brief(self):
        db.session.add(Brief(data={'requirementsLength': '2 weeks'}, framework=self.framework, lot=self.lot,
                             published_at=datetime(2016, 3, 3, 12, 30, 1, 2)))
        db.session.commit()
        assert Brief.query.filter(Brief.applications_closed_at == datetime(2016, 3, 17, 23, 59, 59)).count() == 1

    def test_query_brief_applications_closed_at_date_for_mix_of_brief_lengths(self):
        db.session.add(Brief(data={'requirementsLength': '1 week'}, framework=self.framework, lot=self.lot,
                             published_at=datetime(2016, 3, 10, 12, 30, 1, 2)))
        db.session.add(Brief(data={'requirementsLength': '2 weeks'}, framework=self.framework, lot=self.lot,
                             published_at=datetime(2016, 3, 3, 12, 30, 1, 2)))
        db.session.add(Brief(data={}, framework=self.framework, lot=self.lot,
                             published_at=datetime(2016, 3, 3, 12, 30, 1, 2)))
        db.session.commit()
        assert Brief.query.filter(Brief.applications_closed_at == datetime(2016, 3, 17, 23, 59, 59)).count() == 3

    # TODO: add cases for querying created_at/updated_at auto timestamps with freeze_time

    @pytest.mark.parametrize('inclusive,expected_count', [(True, 2), (False, 1)])
    @pytest.mark.parametrize('datestamp_attr', ['published_at', 'withdrawn_at', 'cancelled_at', 'unsuccessful_at'])
    def test_query_brief_has_datetime_field_before_and_after(self, datestamp_attr, inclusive, expected_count):
        new_briefs = [Brief(data={}, framework=self.framework, lot=self.lot) for i in range(3)]
        setattr(new_briefs[0], datestamp_attr, datetime(2016, 12, 31, 23, 59, 59, 999999))  # < date
        setattr(new_briefs[1], datestamp_attr, datetime(2017, 1, 1, 0, 0, 0))  # <= and >= date
        setattr(new_briefs[2], datestamp_attr, datetime(2017, 1, 1, 0, 0, 1))  # > date

        db.session.add_all(new_briefs)
        db.session.commit()

        briefs_before = Brief.query.has_datetime_field_before(
            datestamp_attr, start_datetime=datetime(2017, 1, 1, 0, 0, 0), inclusive=inclusive
        )
        assert briefs_before.count() == expected_count

        briefs_after = Brief.query.has_datetime_field_after(
            datestamp_attr, start_datetime=datetime(2017, 1, 1, 0, 0, 0), inclusive=inclusive
        )
        assert briefs_after.count() == expected_count

    def test_query_brief_has_datetime_field_before_requires_datetime(self):
        with pytest.raises(ValueError) as e:
            Brief.query.has_datetime_field_before('published_on', start_datetime='2017-01-01')
        assert str(e.value) == 'Datetime object required'

    def test_query_brief_has_datetime_field_after_requires_datetime(self):
        with pytest.raises(ValueError) as e:
            Brief.query.has_datetime_field_after('published_on', start_datetime='2017-01-01')
        assert str(e.value) == 'Datetime object required'

    @pytest.mark.parametrize('inclusive,expected_count', [(True, 2), (False, 0)])
    @pytest.mark.parametrize('datestamp_attr', ['published_at', 'withdrawn_at', 'cancelled_at', 'unsuccessful_at'])
    def test_query_brief_has_datetime_field_between(self, datestamp_attr, inclusive, expected_count):
        new_briefs = [Brief(data={}, framework=self.framework, lot=self.lot) for i in range(4)]
        setattr(new_briefs[0], datestamp_attr, datetime(2016, 12, 31, 23, 59, 59, 999999))  # < date range
        setattr(new_briefs[1], datestamp_attr, datetime(2017, 1, 1, 0, 0, 0))  # <= date range
        setattr(new_briefs[2], datestamp_attr, datetime(2017, 1, 3, 0, 0, 0))  # >= date range
        setattr(new_briefs[3], datestamp_attr, datetime(2017, 1, 3, 0, 0, 1))  # > date range

        db.session.add_all(new_briefs)
        db.session.commit()

        briefs = Brief.query.has_datetime_field_between(
            datestamp_attr,
            start_datetime=datetime(2017, 1, 1, 0, 0, 0),
            end_datetime=datetime(2017, 1, 3, 0, 0, 0),
            inclusive=inclusive
        )
        assert briefs.count() == expected_count

    @pytest.mark.parametrize(
        'start_date,end_date', [
            ('2017-01-01', datetime(2017, 1, 2)), (datetime(2017, 1, 1), '2017-01-02'), ('2017-01-01', '2017-01-03'),
        ]
    )
    def test_query_brief_has_datetime_field_between_requires_datetime(self, start_date, end_date):
        with pytest.raises(ValueError) as e:
            Brief.query.has_datetime_field_between('published_at', start_datetime=start_date, end_datetime=end_date)
        assert str(e.value) == 'Datetime object required'


class TestAwardedBriefs(BaseApplicationTest, FixtureMixin):
    def setup(self):
        super(TestAwardedBriefs, self).setup()
        self.framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
        self.lot = self.framework.get_lot('digital-outcomes')

    def _setup_brief_and_awarded_brief_response(self, awarded_at=True, pending=True):
        self.setup_dummy_suppliers(1)
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1))
        brief_response = BriefResponse(
            brief=brief,
            supplier_id=0,
            data={'boo': 'far'},
            created_at=datetime.utcnow(),
            submitted_at=datetime.utcnow()
        )
        db.session.add_all([brief, brief_response])
        db.session.commit()
        brief_response.award_details = {'pending': True} if pending else {'confirmed': 'details'}
        if awarded_at:
            brief_response.awarded_at = datetime(2016, 1, 1)
        db.session.add(brief_response)
        db.session.commit()
        return brief.id, brief_response.id

    def test_awarded_brief_response_when_there_is_an_award(self):
        self.setup_dummy_suppliers(1)
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1))
        brief_response1 = BriefResponse(brief=brief, supplier_id=0, submitted_at=datetime.utcnow(), data={})
        brief_response2 = BriefResponse(brief=brief, supplier_id=0, submitted_at=datetime.utcnow(), data={})
        brief_response2.award_details = {"confirmed": "details"}
        brief_response2.awarded_at = datetime(2016, 12, 12, 1, 1, 1)
        db.session.add_all([brief, brief_response1, brief_response2])
        db.session.commit()

        brief = Brief.query.get(brief.id)
        assert brief.awarded_brief_response.id == brief_response2.id

    def test_no_awarded_brief_response_if_brief_responses_but_no_award(self):
        self.setup_dummy_suppliers(1)
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1))
        brief_response1 = BriefResponse(brief=brief, supplier_id=0, submitted_at=datetime.utcnow(), data={})
        brief_response2 = BriefResponse(brief=brief, supplier_id=0, submitted_at=datetime.utcnow(), data={})
        db.session.add_all([brief, brief_response1, brief_response2])
        db.session.commit()

        brief = Brief.query.get(brief.id)
        assert brief.awarded_brief_response is None

    def test_no_awarded_brief_response_if_no_brief_responses(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1))
        db.session.add(brief)
        db.session.commit()

        brief = Brief.query.get(brief.id)
        assert brief.awarded_brief_response is None

    def test_brief_serialize_includes_awarded_brief_response_id_if_overall_status_awarded(self):
        brief_id, brief_response_id = self._setup_brief_and_awarded_brief_response(pending=False)
        brief = Brief.query.get(brief_id)
        assert brief.status == 'awarded'
        with mock.patch('app.models.main.url_for') as url_for:
            url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
            assert brief.serialize().get('awardedBriefResponseId') == brief_response_id

    def test_brief_serialize_does_not_include_awarded_brief_response_if_award_is_pending(self):
        brief_id, brief_response_id = self._setup_brief_and_awarded_brief_response(awarded_at=False)
        brief = Brief.query.get(brief_id)
        assert brief.status == 'closed'
        with mock.patch('app.models.main.url_for') as url_for:
            url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
            assert brief.serialize().get('awardedBriefResponseId') is None

    def test_brief_serialize_does_not_include_awarded_brief_response_if_no_awarded_brief_response(self):
        brief = Brief(data={}, framework=self.framework, lot=self.lot, published_at=datetime(2000, 1, 1))
        db.session.add(brief)
        db.session.commit()
        brief = Brief.query.get(brief.id)
        assert brief.status == 'closed'
        with mock.patch('app.models.main.url_for') as url_for:
            url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
            assert brief.serialize().get('awardedBriefResponseId') is None


class TestCopyBrief(BaseApplicationTest, FixtureMixin):

    def setup(self, *args, **kwargs):
        super(TestCopyBrief, self).setup(*args, **kwargs)
        self.setup_dummy_user(role='buyer')
        self.framework = Framework.query.filter(
            Framework.slug == 'digital-outcomes-and-specialists',
        ).one()
        self.lot = self.framework.get_lot('digital-outcomes')

        self.brief = Brief(
            data={'title': 'my title'},
            framework=self.framework,
            lot=self.lot,
            users=User.query.all(),
            status="live"
        )
        db.session.add(self.brief)
        question = BriefClarificationQuestion(
            brief=self.brief,
            question='hi',
            answer='there',
        )
        db.session.add(question)
        db.session.commit()

    def test_copy_brief(self, live_dos_framework):
        copy = self.brief.copy()

        assert copy.framework == self.brief.framework
        assert copy.lot == self.brief.lot
        assert copy.users == self.brief.users
        assert copy.is_a_copy is True

    def test_clarification_questions_not_copied(self, live_dos_framework):
        copy = self.brief.copy()

        assert not copy.clarification_questions

    def test_copied_brief_status_is_draft(self, live_dos_framework):
        copy = self.brief.copy()

        assert copy.status == 'draft'

    def test_brief_title_under_96_chars_adds_copy_string(self, live_dos_framework):
        title = 't' * 95
        self.brief.data['title'] = title
        copy = self.brief.copy()

        assert copy.data['title'] == title + ' copy'

    def test_brief_title_over_95_chars_does_not_add_copy_string(self, live_dos_framework):
        title = 't' * 96
        self.brief.data['title'] = title
        copy = self.brief.copy()

        assert copy.data['title'] == title

    def test_fields_to_remove_are_removed_on_copy(self, live_dos_framework):
        self.brief.data = {
            "other key": "to be kept",
            "startDate": "21-4-2016",
            "questionAndAnswerSessionDetails": "details",
            "researchDates": "some date"
        }
        copy = self.brief.copy()
        assert copy.data == {"other key": "to be kept"}

    def test_copy_is_put_on_live_framework(self, expired_dos_framework, live_dos2_framework):
        """If brief is on framework which is not live its copy chould be moved to the live framework."""
        expired_framework = Framework.query.filter(Framework.id == expired_dos_framework['id']).first()
        live_framework = Framework.query.filter(Framework.id == live_dos2_framework['id']).first()
        self.brief.framework = expired_framework

        copy = self.brief.copy()

        assert copy.framework == live_framework


class TestBriefResponses(BaseApplicationTest, FixtureMixin):
    def setup(self):
        super(TestBriefResponses, self).setup()
        framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
        self.brief_title = 'My Test Brief Title'
        self.brief = self._create_brief()
        db.session.add(self.brief)
        db.session.commit()
        self.brief_id = self.brief.id

        self.setup_dummy_suppliers(1)
        self.supplier = Supplier.query.filter(Supplier.supplier_id == 0).first()
        supplier_framework = SupplierFramework(
            supplier=self.supplier,
            framework=framework,
            declaration={}
        )
        db.session.add(supplier_framework)
        db.session.commit()

    def _create_brief(self, published_at=datetime(2016, 3, 3, 12, 30, 1, 3)):
        framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
        lot = framework.get_lot('digital-outcomes')
        return Brief(
            data={'title': self.brief_title, 'requirementsLength': '1 week'},
            framework=framework,
            lot=lot,
            published_at=published_at
        )

    def test_create_a_new_brief_response(self):
        brief_response = BriefResponse(data={}, brief=self.brief, supplier=self.supplier)
        db.session.add(brief_response)
        db.session.commit()

        assert brief_response.id is not None
        assert brief_response.supplier_id == 0
        assert brief_response.brief_id == self.brief.id
        assert isinstance(brief_response.created_at, datetime)
        assert brief_response.data == {}

    def test_foreign_fields_are_removed_from_brief_response_data(self):
        brief_response = BriefResponse(data={})
        brief_response.data = {'foo': 'bar', 'briefId': 5, 'supplierId': 100}

        assert brief_response.data == {'foo': 'bar'}

    def test_nulls_are_removed_from_brief_response_data(self):
        brief_response = BriefResponse(data={})
        brief_response.data = {'foo': 'bar', 'bar': None}

        assert brief_response.data == {'foo': 'bar'}

    def test_whitespace_is_stripped_from_brief_response_data(self):
        brief_response = BriefResponse(data={})
        brief_response.data = {'foo': ' bar ', 'bar': ['', '  foo', {'evidence': ' some '}]}

        assert brief_response.data == {'foo': 'bar', 'bar': ['foo', {'evidence': 'some'}]}

    def test_submitted_status_for_brief_response_with_submitted_at(self):
        brief_response = BriefResponse(created_at=datetime.utcnow(), submitted_at=datetime.utcnow())
        assert brief_response.status == 'submitted'

    def test_draft_status_for_brief_response_with_no_submitted_at(self):
        brief_response = BriefResponse(created_at=datetime.utcnow())
        assert brief_response.status == 'draft'

    def test_awarded_status_for_brief_response_with_awarded_at_datestamp(self):
        brief = Brief.query.get(self.brief_id)
        brief_response = BriefResponse(
            brief=brief,
            data={},
            supplier_id=0,
            submitted_at=datetime.utcnow(),
            award_details={'pending': True},
        )
        brief_response.award_details = {'confirmed': 'details'}
        brief_response.awarded_at = datetime(2016, 1, 1)
        db.session.add(brief_response)
        db.session.commit()

        assert BriefResponse.query.filter(BriefResponse.status == 'awarded').count() == 1

    def test_awarded_status_for_pending_awarded_brief_response(self):
        brief = Brief.query.get(self.brief_id)
        brief_response = BriefResponse(
            brief=brief,
            data={},
            supplier_id=0,
            submitted_at=datetime.utcnow(),
            award_details={'pending': True}
        )
        db.session.add(brief_response)
        db.session.commit()

        assert BriefResponse.query.filter(BriefResponse.status == 'pending-awarded').count() == 1

    def test_query_draft_brief_response(self):
        db.session.add(BriefResponse(brief_id=self.brief_id, supplier_id=0, data={}))
        db.session.commit()

        assert BriefResponse.query.filter(BriefResponse.status == 'draft').count() == 1
        assert BriefResponse.query.filter(BriefResponse.status == 'submitted').count() == 0

        # Check python implementation gives same result as the sql implementation
        assert BriefResponse.query.all()[0].status == 'draft'

    def test_query_submitted_brief_response(self):
        db.session.add(BriefResponse(
            brief_id=self.brief_id, supplier_id=0, submitted_at=datetime.utcnow(),
            data={})
        )
        db.session.commit()

        assert BriefResponse.query.filter(BriefResponse.status == 'submitted').count() == 1
        assert BriefResponse.query.filter(BriefResponse.status == 'draft').count() == 0

        # Check python implementation gives same result as the sql implementation
        assert BriefResponse.query.all()[0].status == 'submitted'

    def test_brief_response_can_be_serialized(self):
        brief_response = BriefResponse(
            data={'foo': 'bar'}, brief=self.brief, supplier=self.supplier, submitted_at=datetime(2016, 9, 28)
        )
        db.session.add(brief_response)
        db.session.commit()

        with mock.patch('app.models.main.url_for') as url_for:
            url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
            assert brief_response.serialize() == {
                'id': brief_response.id,
                'brief': {
                    'applicationsClosedAt': '2016-03-10T23:59:59.000000Z',
                    'id': self.brief.id,
                    'status': self.brief.status,
                    'title': self.brief_title,
                    'framework': {
                        'family': 'digital-outcomes-and-specialists',
                        'name': 'Digital Outcomes and Specialists',
                        'slug': 'digital-outcomes-and-specialists',
                        'status': self.brief.framework.status
                    }
                },
                'briefId': self.brief.id,
                'supplierId': 0,
                'supplierName': 'Supplier 0',
                'supplierOrganisationSize': 'small',
                'createdAt': mock.ANY,
                'submittedAt': '2016-09-28T00:00:00.000000Z',
                'status': 'submitted',
                'foo': 'bar',
                'links': {
                    'self': (('main.get_brief_response',), {'brief_response_id': brief_response.id}),
                    'brief': (('main.get_brief',), {'brief_id': self.brief.id}),
                    'supplier': (('main.get_supplier',), {'supplier_id': 0}),
                }
            }

    def test_brief_response_can_be_serialized_with_data_false(self):
        brief_response = BriefResponse(
            data={
                'foo': 'bar',
                'essentialRequirementsMet': 'true',
            },
            brief=self.brief,
            supplier=self.supplier,
            submitted_at=datetime(2016, 9, 28),
        )
        db.session.add(brief_response)
        db.session.commit()

        with mock.patch('app.models.main.url_for') as url_for:
            url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
            assert brief_response.serialize(with_data=False) == {
                'id': brief_response.id,
                'brief': {
                    'applicationsClosedAt': '2016-03-10T23:59:59.000000Z',
                    'id': self.brief.id,
                    'status': self.brief.status,
                    'title': self.brief_title,
                    'framework': {
                        'family': 'digital-outcomes-and-specialists',
                        'name': 'Digital Outcomes and Specialists',
                        'slug': 'digital-outcomes-and-specialists',
                        'status': self.brief.framework.status
                    }
                },
                'briefId': self.brief.id,
                'supplierId': 0,
                'supplierName': 'Supplier 0',
                'supplierOrganisationSize': 'small',
                'createdAt': mock.ANY,
                'submittedAt': '2016-09-28T00:00:00.000000Z',
                'status': 'submitted',
                'essentialRequirementsMet': 'true',
                'links': {
                    'self': (('main.get_brief_response',), {'brief_response_id': brief_response.id}),
                    'brief': (('main.get_brief',), {'brief_id': self.brief.id}),
                    'supplier': (('main.get_supplier',), {'supplier_id': 0}),
                }
            }

    def test_brief_response_can_be_serialized_with_no_submitted_at_time(self):
        brief_response = BriefResponse(
            data={'foo': 'bar'}, brief=self.brief, supplier=self.supplier
        )
        db.session.add(brief_response)
        db.session.commit()

        with mock.patch('app.models.main.url_for') as url_for:
            url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
            assert brief_response.serialize() == {
                'id': brief_response.id,
                'briefId': self.brief.id,
                'brief': {
                    'applicationsClosedAt': '2016-03-10T23:59:59.000000Z',
                    'id': self.brief.id,
                    'status': self.brief.status,
                    'title': self.brief_title,
                    'framework': {
                        'family': 'digital-outcomes-and-specialists',
                        'name': 'Digital Outcomes and Specialists',
                        'slug': 'digital-outcomes-and-specialists',
                        'status': self.brief.framework.status
                    }
                },
                'supplierId': 0,
                'supplierName': 'Supplier 0',
                'supplierOrganisationSize': 'small',
                'createdAt': mock.ANY,
                'status': 'draft',
                'foo': 'bar',
                'links': {
                    'self': (('main.get_brief_response',), {'brief_response_id': brief_response.id}),
                    'brief': (('main.get_brief',), {'brief_id': self.brief.id}),
                    'supplier': (('main.get_supplier',), {'supplier_id': 0}),
                }
            }

    def test_brief_response_serialization_includes_award_details_if_status_awarded(self):
        brief_response = BriefResponse(
            data={'foo': 'bar'}, brief=self.brief, supplier=self.supplier, submitted_at=datetime(2016, 9, 28)
        )
        db.session.add(brief_response)
        db.session.commit()
        brief_response.award_details = {
            "awardedContractStartDate": "2020-12-31",
            "awardedContractValue": "99.95"
        }
        brief_response.awarded_at = datetime(2016, 1, 1)
        db.session.add(brief_response)
        db.session.commit()

        with mock.patch('app.models.main.url_for') as url_for:
            url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
            assert brief_response.serialize()['awardDetails'] == {
                "awardedContractStartDate": "2020-12-31",
                "awardedContractValue": "99.95"
            }

    def test_brief_response_serialization_includes_pending_flag_if_status_pending_awarded(self):
        brief_response = BriefResponse(
            data={'foo': 'bar'}, brief=self.brief, supplier=self.supplier, submitted_at=datetime(2016, 9, 28)
        )
        db.session.add(brief_response)
        db.session.commit()
        brief_response.award_details = {"pending": True}
        db.session.add(brief_response)
        db.session.commit()

        with mock.patch('app.models.main.url_for') as url_for:
            url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
            assert brief_response.serialize()['awardDetails'] == {"pending": True}

    def test_brief_response_awarded_at_index_raises_integrity_error_on_more_than_one_award_per_brief(self):
        timestamp = datetime(2016, 12, 31, 12, 1, 2, 3)
        brief = Brief.query.get(self.brief_id)
        brief_response1 = BriefResponse(
            data={}, brief=brief, supplier=self.supplier, submitted_at=datetime.utcnow(),
            award_details={'pending': True},
        )
        brief_response1.award_details = {'confirmed': 'details'}
        brief_response1.awarded_at = timestamp
        brief_response2 = BriefResponse(
            data={}, brief=brief, supplier=self.supplier, submitted_at=datetime.utcnow(),
            award_details={'pending': True},
        )
        brief_response2.award_details = {'confirmed': 'details'}
        brief_response2.awarded_at = timestamp
        db.session.add_all([brief_response1, brief_response2])
        with pytest.raises(IntegrityError) as exc:
            db.session.commit()
        assert 'duplicate key value violates unique constraint' in str(exc.value)

    def test_brief_response_awarded_index_can_save_awards_for_unique_briefs(self):
        timestamp = datetime(2016, 12, 31, 12, 1, 2, 3)
        brief = Brief.query.get(self.brief_id)
        brief2 = self._create_brief()
        db.session.add(brief2)
        brief_response1 = BriefResponse(
            data={}, brief=brief, supplier=self.supplier, submitted_at=datetime.utcnow(),
            award_details={'pending': True}
        )
        brief_response1.awarded_at = timestamp
        brief_response1.award_details = {'confirmed': 'details'}
        brief_response2 = BriefResponse(
            data={}, brief=brief, supplier=self.supplier, submitted_at=datetime.utcnow(),
            award_details={'pending': True}, awarded_at=None
        )
        brief_response3 = BriefResponse(
            data={}, brief=brief2, supplier=self.supplier, submitted_at=datetime.utcnow(),
            award_details={'pending': True}, awarded_at=None
        )
        brief_response4 = BriefResponse(
            data={}, brief=brief2, supplier=self.supplier, submitted_at=datetime.utcnow(),
            award_details={'pending': True}
        )
        brief_response4.awarded_at = timestamp
        brief_response4.award_details = {'confirmed': 'details'}

        db.session.add_all([brief_response1, brief_response2, brief_response3, brief_response4])
        db.session.commit()

        for b in [brief_response1, brief_response2, brief_response3, brief_response4]:
            assert b.id

    def test_brief_response_awarded_index_can_save_multiple_non_awarded_responses(self):
        brief = Brief.query.get(self.brief_id)
        brief_response1 = BriefResponse(
            data={}, brief=brief, supplier=self.supplier, submitted_at=datetime.utcnow(), awarded_at=None
        )
        brief_response2 = BriefResponse(
            data={}, brief=brief, supplier=self.supplier, submitted_at=datetime.utcnow(), awarded_at=None
        )
        db.session.add_all([brief_response1, brief_response2])
        db.session.commit()

        for b in [brief_response1, brief_response2]:
            assert b.id

    def test_brief_response_awarded_index_sets_default_value(self):
        brief_response = BriefResponse(data={}, brief=self.brief, supplier=self.supplier)
        db.session.add(brief_response)
        db.session.commit()

        assert brief_response.id
        assert brief_response.awarded_at is None

    def test_brief_response_can_not_be_awarded_if_brief_is_not_closed(self):
        with pytest.raises(ValidationError) as e:
            brief = self._create_brief(published_at=datetime.utcnow())
            brief_response = BriefResponse(data={}, brief=brief, supplier=self.supplier)
            db.session.add_all([brief, brief_response])
            db.session.commit()

            existing_brief_response = BriefResponse.query.get(brief_response.id)
            existing_brief_response.awarded_at = datetime(2016, 12, 31, 12, 1, 1)
            db.session.add(existing_brief_response)
            db.session.commit()

        assert 'Brief response can not be awarded if the brief is not closed' in e.value.message

    def test_brief_response_can_not_be_awarded_if_brief_response_has_not_been_submitted(self):
        with pytest.raises(ValidationError) as e:
            brief_response = BriefResponse(data={}, brief=self.brief, supplier=self.supplier)
            db.session.add(brief_response)
            db.session.commit()

            existing_brief_response = BriefResponse.query.get(brief_response.id)
            existing_brief_response.awarded_at = datetime(2016, 12, 31, 12, 1, 1)
            db.session.add(existing_brief_response)
            db.session.commit()

        assert 'Brief response can not be awarded if response has not been submitted' in e.value.message

    def test_can_remove_award_details_from_brief_response_if_brief_not_awarded(self):
        brief_response = BriefResponse(
            data={}, brief=self.brief, supplier=self.supplier, submitted_at=datetime.utcnow()
        )
        db.session.add(brief_response)
        db.session.commit()
        # Pending award to this brief response
        brief_response.award_details = {'pending': True}
        db.session.add(brief_response)
        db.session.commit()
        # There's still time to change our minds...
        brief_response.award_details = {}
        db.session.add(brief_response)
        db.session.commit()

    def test_can_remove_award_details_from_brief_response_if_brief_awarded(self):
        brief_response = BriefResponse(
            data={}, brief=self.brief, supplier=self.supplier, submitted_at=datetime.utcnow()
        )
        db.session.add(brief_response)
        db.session.commit()
        # Award to this brief response
        brief_response.award_details = {'confirmed': 'details'}
        brief_response.awarded_at = datetime.utcnow()
        db.session.add(brief_response)
        db.session.commit()
        # There's still time to change our minds...
        brief_response.awarded_at = None
        brief_response.award_details = {}
        db.session.add(brief_response)
        db.session.commit()

        assert brief_response.awarded_at is None

    def test_cannot_change_award_date_in_brief_response_if_brief_awarded(self):
        with pytest.raises(ValidationError) as e:
            brief_response = BriefResponse(
                data={}, brief=self.brief, supplier=self.supplier, submitted_at=datetime.utcnow()
            )
            db.session.add(brief_response)
            db.session.commit()
            # Confirm award to this brief response
            brief_response.award_details = {'confirmed': 'details'}
            brief_response.awarded_at = datetime.utcnow()
            db.session.add(brief_response)
            db.session.commit()
            # We've changed our minds again but it's too late...
            brief_response.awarded_at = datetime.utcnow()

        assert 'Cannot change award datestamp on previously awarded Brief Response' in e.value.message

    def test_brief_response_serialize_keys_match_api_stub_keys(self):
        # Ensures our dmtestutils.api_model_stubs are kept up to date
        brief_response = BriefResponse(
            data={
                'availability': '02/01/2018',
                'essentialRequirements': [],
                'essentialRequirementsMet': True,
                'niceToHaveRequirements': [],
                'respondToEmailAddress': 'davidbowie@example.com'
            },
            brief=self.brief, supplier=self.supplier, submitted_at=datetime(2016, 9, 28)
        )
        db.session.add(brief_response)
        db.session.commit()

        with mock.patch('app.models.main.url_for') as url_for:
            url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
            assert sorted(brief_response.serialize().keys()) == sorted(BriefResponseStub().response().keys())


class TestBriefClarificationQuestion(BaseApplicationTest):
    def setup(self):
        super(TestBriefClarificationQuestion, self).setup()
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
        brief = Brief(data={}, framework=self.framework, lot=self.lot, status="draft")
        with pytest.raises(ValidationError) as e:
            BriefClarificationQuestion(brief=brief, question="Why?", answer="Because")

        assert str(e.value.message) == "Brief status must be 'live', not 'draft'"

    def test_cannot_update_brief_by_id(self):
        with pytest.raises(ValidationError) as e:
            BriefClarificationQuestion(brief_id=self.brief.id, question="Why?", answer="Because")

        assert str(e.value.message) == "Cannot update brief_id directly, use brief relationship"

    def test_published_at_is_set_on_creation(self):
        question = BriefClarificationQuestion(
            brief=self.brief, question="Why?", answer="Because")

        db.session.add(question)
        db.session.commit()

        assert isinstance(question.published_at, datetime)

    def test_question_must_not_be_null(self):
        with pytest.raises(IntegrityError):
            question = BriefClarificationQuestion(brief=self.brief, answer="Because")

            db.session.add(question)
            db.session.commit()

    def test_question_must_not_be_empty(self):
        with pytest.raises(ValidationError) as e:
            question = BriefClarificationQuestion(brief=self.brief, question="", answer="Because")
            question.validate()

        assert e.value.message["question"] == "answer_required"

    def test_questions_must_not_be_more_than_100_words(self):
        long_question = " ".join(["word"] * 101)
        with pytest.raises(ValidationError) as e:
            question = BriefClarificationQuestion(brief=self.brief, question=long_question, answer="Because")
            question.validate()

        assert e.value.message["question"] == "under_100_words"

    def test_question_must_not_be_more_than_5000_characters(self):
        long_question = "a" * 5001
        with pytest.raises(ValidationError) as e:
            question = BriefClarificationQuestion(brief=self.brief, question=long_question, answer="Because")
            question.validate()

        assert e.value.message["question"] == "under_character_limit"

    def test_questions_can_be_100_words(self):
        question = " ".join(["word"] * 100)
        question = BriefClarificationQuestion(brief=self.brief, question=question, answer="Because")
        question.validate()

    def test_answer_must_not_be_null(self):
        with pytest.raises(IntegrityError):
            question = BriefClarificationQuestion(brief=self.brief, question="Why?")

            db.session.add(question)
            db.session.commit()

    def test_answer_must_not_be_empty(self):
        with pytest.raises(ValidationError) as e:
            question = BriefClarificationQuestion(brief=self.brief, question="Why?", answer="")
            question.validate()

        assert e.value.message["answer"] == "answer_required"

    def test_answers_must_not_be_more_than_100_words(self):
        long_answer = " ".join(["word"] * 101)
        with pytest.raises(ValidationError) as e:
            question = BriefClarificationQuestion(brief=self.brief, question="Why?", answer=long_answer)
            question.validate()

        assert e.value.message["answer"] == "under_100_words"

    def test_answer_must_not_be_more_than_5000_characters(self):
        long_answer = "a" * 5001
        with pytest.raises(ValidationError) as e:
            question = BriefClarificationQuestion(brief=self.brief, question="Why?", answer=long_answer)
            question.validate()

        assert e.value.message["answer"] == "under_character_limit"

    def test_answers_can_be_100_words(self):
        answer = " ".join(["word"] * 100)
        question = BriefClarificationQuestion(brief=self.brief, question="Why?", answer=answer)
        question.validate()


class TestSuppliers(BaseApplicationTest, FixtureMixin):
    def setup(self):
        super(TestSuppliers, self).setup()
        self.setup_dummy_suppliers(1)
        self.supplier = Supplier.query.filter(Supplier.supplier_id == 0).first()
        self.contact_id = ContactInformation.query.filter(
            ContactInformation.supplier_id == self.supplier.supplier_id
        ).first().id

    def _update_supplier_from_json_with_all_details(self):
        update_data = {
            "id": 90006000,
            "supplierId": "DO_NOT_UPDATE_ME",
            "name": "String and Sticky Tape Inc.",
            "dunsNumber": "01010101",
            "description": "All your parcel wrapping needs catered for",
            "companiesHouseNumber": "98765432",
            "registeredName": "Tape and String Inc.",
            "registrationCountry": "country:GB",
            "vatNumber": "321321321",
            "organisationSize": "medium",
            "tradingStatus": "sole trader",
            "companyDetailsConfirmed": False,
        }
        self.supplier.update_from_json(update_data)

    def test_serialization_of_new_supplier(self):
        with mock.patch('app.models.main.url_for') as url_for:
            url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
            assert self.supplier.serialize() == {
                'contactInformation': [
                    {
                        'contactName': u'Contact for Supplier 0',
                        'email': u'0@contact.com',
                        'id': self.contact_id,
                        'links': {
                            'self': (
                                ('main.update_contact_information',),
                                {'contact_id': self.contact_id, 'supplier_id': 0}
                            )
                        },
                        'address1': '7 Gem Lane',
                        'city': 'Cantelot',
                        'postcode': 'SW1A 1AA',
                        'personalDataRemoved': False,
                    }
                ],
                'description': u'',
                'id': 0,
                'links': {
                    'self': (('main.get_supplier',), {'supplier_id': 0})
                },
                'name': u'Supplier 0',
                'companyDetailsConfirmed': False,
                'organisationSize': 'small',
                'dunsNumber': '100000000',
                'registeredName': 'Registered Supplier Name 0',
                'companiesHouseNumber': '12345670',
                'otherCompanyRegistrationNumber': '555-222-111',
                'registrationCountry': 'country:GB'
            }

    def test_update_from_json(self):
        initial_id = self.supplier.id
        initial_sid = self.supplier.supplier_id

        self._update_supplier_from_json_with_all_details()

        # Check IDs can't be updated
        assert self.supplier.id == initial_id
        assert self.supplier.supplier_id == initial_sid

        # Check everything else has been updated to the correct value
        assert self.supplier.name == "String and Sticky Tape Inc."
        assert self.supplier.duns_number == "01010101"
        assert self.supplier.description == "All your parcel wrapping needs catered for"
        assert self.supplier.companies_house_number == "98765432"
        assert self.supplier.registered_name == "Tape and String Inc."
        assert self.supplier.registration_country == "country:GB"
        assert self.supplier.vat_number == "321321321"
        assert self.supplier.organisation_size == "medium"
        assert self.supplier.trading_status == "sole trader"
        assert self.supplier.company_details_confirmed is False

        # Check that serialization of a supplier with all details added looks as it should
        with mock.patch('app.models.main.url_for') as url_for:
            url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
            assert self.supplier.serialize() == {
                'companiesHouseNumber': '98765432',
                'contactInformation': [
                    {
                        'contactName': u'Contact for Supplier 0',
                        'email': u'0@contact.com',
                        'id': self.contact_id,
                        'links': {
                            'self': (
                                ('main.update_contact_information',),
                                {'contact_id': self.contact_id, 'supplier_id': 0}
                            )
                        },
                        'address1': '7 Gem Lane',
                        'city': 'Cantelot',
                        'postcode': 'SW1A 1AA',
                        'personalDataRemoved': False,
                    }
                ],
                'description': 'All your parcel wrapping needs catered for',
                'dunsNumber': '01010101',
                'id': 0,
                'links': {'self': (('main.get_supplier',), {'supplier_id': 0})},
                'name': 'String and Sticky Tape Inc.',
                'organisationSize': 'medium',
                'registeredName': 'Tape and String Inc.',
                'registrationCountry': 'country:GB',
                'tradingStatus': 'sole trader',
                'companyDetailsConfirmed': False,
                'vatNumber': '321321321',
            }

    def test_supplier_serialize_keys_match_api_stub_keys(self):
        # Ensures our dmtestutils.api_model_stubs are kept up to date
        self._update_supplier_from_json_with_all_details()
        supplier_stub = SupplierStub(id=0, contact_id=self.contact_id)
        with mock.patch('app.models.main.url_for') as url_for:
            url_for.side_effect = lambda *args, **kwargs: (args, kwargs)
            assert sorted(self.supplier.serialize().keys()) == sorted(supplier_stub.response().keys())


class TestServices(BaseApplicationTest, FixtureMixin):
    def test_framework_is_live_only_returns_live_frameworks(self):
        # the side effect of this method is to create four suppliers with ids between 0-3
        self.setup_dummy_services_including_unpublished(1)
        self.setup_dummy_service(
            service_id='1000000000',
            supplier_id=0,
            status='published',
            framework_id=2)

        services = Service.query.framework_is_live()

        assert Service.query.count() == 4
        assert services.count() == 3
        assert(all(s.framework.status == 'live' for s in services))

    def test_lot_must_be_associated_to_the_framework(self):
        self.setup_dummy_suppliers(1)
        with pytest.raises(IntegrityError) as excinfo:
            self.setup_dummy_service(
                service_id='10000000001',
                supplier_id=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=1)  # SaaS

        assert 'not present in table "framework_lots"' in "{}".format(excinfo.value)

    def test_default_ordering(self):
        def add_service(service_id, framework_id, lot_id, service_name):
            self.setup_dummy_service(
                service_id=service_id,
                supplier_id=0,
                framework_id=framework_id,
                lot_id=lot_id,
                data={'serviceName': service_name})

        self.setup_dummy_suppliers(1)
        add_service('1000000990', 3, 3, 'zzz')
        add_service('1000000991', 3, 3, 'aaa')
        add_service('1000000992', 3, 1, 'zzz')
        add_service('1000000993', 1, 3, 'zzz')
        db.session.commit()

        services = Service.query.default_order()

        assert [s.service_id for s in services] == ['1000000993', '1000000992', '1000000991', '1000000990']

    def test_has_statuses(self):
        self.setup_dummy_services_including_unpublished(1)

        services = Service.query.has_statuses('published')

        assert services.count() == 1

    def test_in_lot(self):
        self.setup_dummy_suppliers(1)
        self.setup_dummy_service(
            service_id='10000000001',
            supplier_id=0,
            framework_id=5,  # Digital Outcomes and Specialists
            lot_id=5)  # digital-outcomes
        self.setup_dummy_service(
            service_id='10000000002',
            supplier_id=0,
            framework_id=5,  # Digital Outcomes and Specialists
            lot_id=6)  # digital-specialists
        self.setup_dummy_service(
            service_id='10000000003',
            supplier_id=0,
            framework_id=5,  # Digital Outcomes and Specialists
            lot_id=6)  # digital-specialists

        services = Service.query.in_lot('digital-specialists')
        assert services.count() == 2

    def test_data_has_key(self):
        self.setup_dummy_suppliers(1)
        self.setup_dummy_service(
            service_id='10000000001',
            supplier_id=0,
            framework_id=5,  # Digital Outcomes and Specialists
            lot_id=6,  # digital-specialists
            data={'key1': 'foo', 'key2': 'bar'})
        self.setup_dummy_service(
            service_id='10000000002',
            supplier_id=0,
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
        self.setup_dummy_suppliers(1)
        self.setup_dummy_service(
            service_id='10000000001',
            supplier_id=0,
            framework_id=5,  # Digital Outcomes and Specialists
            lot_id=6,  # digital-specialists
            data={'key1': ['foo1', 'foo2'], 'key2': ['bar1']})
        self.setup_dummy_service(
            service_id='10000000002',
            supplier_id=0,
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

        assert service.status == 'enabled'

    def test_invalid_service_status(self):
        service = Service()
        with pytest.raises(ValidationError):
            service.status = 'invalid'

    def test_has_statuses_should_accept_multiple_statuses(self):
        self.setup_dummy_services_including_unpublished(1)

        services = Service.query.has_statuses('published', 'disabled')

        assert services.count() == 2

    def test_update_from_json(self):
        self.setup_dummy_suppliers(2)
        self.setup_dummy_service(
            service_id='1000000000',
            supplier_id=0,
            status='published',
            framework_id=2)

        service = Service.query.filter(Service.service_id == '1000000000').first()

        updated_at = service.updated_at
        created_at = service.created_at

        service.update_from_json({'foo': 'bar', 'supplierId': 1})

        db.session.add(service)
        db.session.commit()

        assert service.created_at == created_at
        assert service.updated_at > updated_at
        assert service.data == {'foo': 'bar', 'serviceName': 'Service 1000000000'}
        assert service.supplier_id == 1

    def test_updating_service_with_nonexistent_supplier_raises_error(self):
        self.setup_dummy_suppliers(1)
        self.setup_dummy_service(
            service_id='1000000000',
            supplier_id=0,
            status='published',
            framework_id=2)

        service = Service.query.filter(Service.service_id == '1000000000').first()
        service.update_from_json({'supplierId': 999})

        db.session.add(service)
        with pytest.raises(IntegrityError) as exc:
            db.session.commit()
        assert 'insert or update on table "services" violates foreign key constraint' in str(exc.value)

    def test_service_serialize_matches_api_stub_response(self):
        # Ensures our dmtestutils.api_model_stubs are kept up to date
        self.framework_id = \
            self.setup_dummy_framework("g-cloud-11", "g-cloud", "G-Cloud 11", id=111)
        self.supplier_id = self.setup_dummy_suppliers(1)[0]

        model = Service(
            data={"serviceName": "Pie Mania"},
            framework_id=self.framework_id,
            lot_id=11,  # cloud-support
            service_id="1010101010",
            status="published",
            supplier_id=self.supplier_id,
            created_at="2018-04-07T12:34:00.000000Z",
            updated_at="2019-05-08T13:24:00.000000Z",
        )
        db.session.add(model)
        db.session.commit()

        stub = ServiceStub(
            service_id="1010101010",
            framework_slug="g-cloud-11",
            lot="cloud-support",
            lot_slug="cloud-support",
            lot_name="Cloud support",
            service_name="Pie Mania",
            status="published",
            supplier_id=self.supplier_id,
            supplier_name="Supplier 0",
            created_at="2018-04-07T12:34:00.000000Z",
            updated_at="2019-05-08T13:24:00.000000Z",
        )

        assert model.serialize() == stub.response()


class TestDraftService(BaseApplicationTest, FixtureMixin):
    def setup(self):
        super().setup()

        self.setup_dummy_suppliers(1)
        self.setup_dummy_service(
            service_id='1000000000',
            supplier_id=0,
            status='published',
            framework_id=2)

    def test_from_service(self):
        service = Service.query.filter(Service.service_id == '1000000000').first()
        draft_service = DraftService.from_service(service)

        db.session.add(draft_service)
        db.session.commit()

        assert draft_service.framework_id == service.framework_id
        assert draft_service.lot == service.lot
        assert draft_service.service_id == service.service_id
        assert draft_service.supplier == service.supplier
        assert draft_service.data == service.data
        assert draft_service.status == service.status

    def test_from_service_with_target_framework_id_and_copiable_questions(self):
        service = Service.query.filter(Service.service_id == '1000000000').first()
        service.data.update(
            questionOne='Question one',
            questionTwo='Question two',
            questionThree='Question three'
        )

        draft_service = DraftService.from_service(
            service,
            questions_to_copy=['serviceName', 'questionOne', 'questionThree'],
            target_framework_id=3,
        )

        db.session.add(draft_service)
        db.session.commit()

        assert draft_service.framework_id == 3
        assert draft_service.lot == service.lot
        assert draft_service.service_id is None
        assert draft_service.supplier == service.supplier
        assert draft_service.status == 'not-submitted'
        assert draft_service.data == {
            'serviceName': 'Service 1000000000',
            'questionOne': 'Question one',
            'questionThree': 'Question three',
        }

    def test_from_service_with_target_framework_id_and_excluded_questions(self):
        service = Service.query.filter(Service.service_id == '1000000000').first()
        service.data.update(
            questionOne='Question one',
            questionTwo='Question two',
            questionThree='Question three'
        )

        draft_service = DraftService.from_service(
            service,
            questions_to_exclude=['serviceName', 'questionOne', 'questionThree'],
            target_framework_id=3,
        )

        db.session.add(draft_service)
        db.session.commit()

        for question in ['serviceName', 'questionOne', 'questionThree']:
            assert question not in draft_service.data

    def test_from_service_copies_status_if_target_framework_id_is_the_same(self):
        service = Service.query.filter(Service.service_id == '1000000000').first()
        draft_service = DraftService.from_service(
            service,
            questions_to_copy=['serviceName'],
            target_framework_id=service.framework_id,
        )

        assert draft_service.status == service.status

    def test_draft_service_serialize_matches_api_stub_response(self):
        # Ensures our dmtestutils.api_model_stubs are kept up to date
        framework_id = self.setup_dummy_framework("g-cloud-11", "g-cloud", "G-Cloud 11", id=111)
        draft_service = DraftService(
            data={"serviceName": "Pies as a service"},
            framework_id=framework_id,
            lot_id=9,  # cloud-hosting
            supplier_id=0,
            status="enabled",
            created_at="2017-04-07T12:34:00.000000Z",
            updated_at="2017-05-08T13:24:00.000000Z",
            lot_one_service_limit=Lot.query.get(9).one_service_limit,
        )
        db.session.add(draft_service)
        db.session.commit()

        stub = DraftServiceStub(
            id=draft_service.id,
            framework_slug="g-cloud-11",
            lot="cloud-hosting",
            lot_slug="cloud-hosting",
            lot_name="Cloud hosting",
            service_name="Pies as a service",
            status="enabled",
            supplier_id=0,
            supplier_name="Supplier 0",
            created_at="2017-04-07T12:34:00.000000Z",
            updated_at="2017-05-08T13:24:00.000000Z",
        )

        assert draft_service.serialize() == stub.response()

    @pytest.mark.parametrize('lot_slug, expected_count', [('scs', 0), ('saas', 1)])
    def test_draft_service_filtering_by_lot(self, lot_slug, expected_count):
        # Create a single DraftService on the 'saas' lot
        service = Service.query.filter(Service.service_id == '1000000000').first()
        draft_service = DraftService.from_service(service)

        db.session.add(draft_service)
        db.session.commit()

        drafts = DraftService.query.in_lot(lot_slug)
        assert drafts.count() == expected_count


class TestSupplierFrameworks(BaseApplicationTest, FixtureMixin):
    def test_nulls_are_stripped_from_declaration(self):
        supplier_framework = SupplierFramework()
        supplier_framework.declaration = {'foo': 'bar', 'bar': None}

        assert supplier_framework.declaration == {'foo': 'bar'}

    def test_whitespace_values_are_stripped_from_declaration(self):
        supplier_framework = SupplierFramework()
        supplier_framework.declaration = {'foo': ' bar ', 'bar': '', 'other': ' '}

        assert supplier_framework.declaration == {'foo': 'bar', 'bar': '', 'other': ''}

    def test_create_supplier_framework(self):
        # the intention of this test is to ensure a SupplierFramework without any FrameworkAgreements is visible through
        # the default query - i.e. none of our custom relationships are causing it to do an inner join which would
        # cause such a SupplierFramework to be invisible
        self.setup_dummy_suppliers(1)

        supplier_framework = SupplierFramework(supplier_id=0, framework_id=1)
        db.session.add(supplier_framework)
        db.session.commit()

        assert len(
            SupplierFramework.query.filter(
                SupplierFramework.supplier_id == 0
            ).all()
        ) == 1

    def test_prefill_declaration_from_framework(self):
        self.setup_dummy_suppliers(2)

        supplier_framework0 = SupplierFramework(supplier_id=0, framework_id=1)
        db.session.add(supplier_framework0)

        supplier_framework1 = SupplierFramework(
            supplier_id=0,
            framework_id=2,
            prefill_declaration_from_framework_id=1,
        )
        db.session.add(supplier_framework1)

        db.session.commit()

        # check the relationships operate properly
        assert supplier_framework1.prefill_declaration_from_framework is supplier_framework0.framework
        assert supplier_framework1.prefill_declaration_from_supplier_framework is supplier_framework0

        # check the serialization does the right thing
        assert supplier_framework0.serialize()["prefillDeclarationFromFrameworkSlug"] is None
        assert supplier_framework1.serialize()["prefillDeclarationFromFrameworkSlug"] == \
            supplier_framework0.framework.slug

        # before we tear things down we'll test prefill_declaration_from_framework's
        # SupplierFramework->SupplierFramework constraint
        db.session.delete(supplier_framework0)
        with pytest.raises(IntegrityError):
            # this should fail because it removes the sf that supplier_framework1 implicitly points to
            db.session.commit()

    def test_supplier_framework_serialize_keys_match_api_stub_keys(self):
        # Ensures our dmtestutils.api_model_stubs are kept up to date
        self.setup_dummy_suppliers(1)
        supplier_framework = SupplierFramework(supplier_id=0, framework_id=1)
        supplier_framework.declaration = {'foo': 'bar', 'bar': None}
        db.session.add(supplier_framework)
        db.session.commit()

        supplier_framework_stub = SupplierFrameworkStub()
        assert sorted(supplier_framework.serialize().keys()) == sorted(supplier_framework_stub.response().keys())


class TestLot(BaseApplicationTest):

    def setup(self):
        super().setup()
        self.framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
        self.lot = self.framework.get_lot('user-research-studios')

    def test_lot_data_is_serialized(self):
        assert self.lot.serialize() == {
            u'id': 7,
            u'name': u'User research studios',
            u'slug': u'user-research-studios',
            u'allowsBrief': False,
            u'oneServiceLimit': False,
            u'unitSingular': u'research studio',
            u'unitPlural': u'research studios',
        }

    def test_lot_serialize_keys_match_api_stub_keys(self):
        # Ensures our dmtestutils.api_model_stubs are kept up to date
        assert sorted(self.lot.serialize().keys()) == sorted(LotStub().response().keys())


class TestFrameworkSupplierIds(BaseApplicationTest):
    """Test getting supplier ids for framework."""

    def test_1_supplier(self, draft_service):
        """Test that when one supplier exists in the framework that only supplier is shown."""
        ds = DraftService.query.filter(DraftService.service_id == draft_service['serviceId']).first()
        f = Framework.query.filter(Framework.id == ds.framework_id).first()
        supplier_ids_with_completed_service = f.get_supplier_ids_for_completed_service()
        assert len(supplier_ids_with_completed_service) == 1
        assert ds.supplier.supplier_id in supplier_ids_with_completed_service

    def test_submitted_shows(self, draft_service):
        """Test sevice with status 'submitted' is shown."""
        ds = DraftService.query.filter(DraftService.service_id == draft_service['serviceId']).first()
        f = Framework.query.filter(Framework.id == ds.framework_id).first()
        supplier_ids_with_completed_service = f.get_supplier_ids_for_completed_service()
        assert ds.status == 'submitted'
        assert ds.supplier.supplier_id in supplier_ids_with_completed_service

    def test_failed_shows(self, draft_service):
        """Test sevice with status 'failed' is shown."""
        ds = DraftService.query.filter(DraftService.service_id == draft_service['serviceId']).first()
        ds.status = 'failed'
        db.session.add(ds)
        db.session.commit()
        f = Framework.query.filter(Framework.id == ds.framework_id).first()
        supplier_ids_with_completed_service = f.get_supplier_ids_for_completed_service()
        assert ds.status == 'failed'
        assert ds.supplier.supplier_id in supplier_ids_with_completed_service

    def test_not_submitted_does_not_show(self, draft_service):
        """Test sevice with status 'not-submitted' is not shown."""
        ds = DraftService.query.filter(DraftService.service_id == draft_service['serviceId']).first()
        ds.status = 'not-submitted'
        db.session.add(ds)
        db.session.commit()
        f = Framework.query.filter(Framework.id == ds.framework_id).first()
        supplier_ids_with_completed_service = f.get_supplier_ids_for_completed_service()
        assert ds.status == 'not-submitted'
        assert ds.supplier.supplier_id not in supplier_ids_with_completed_service

    def test_no_suppliers(self, open_example_framework):
        """Test a framework with no suppliers on it returns no submitted services."""
        f = Framework.query.filter(Framework.id == open_example_framework['id']).first()
        supplier_ids_with_completed_service = f.get_supplier_ids_for_completed_service()
        assert len(supplier_ids_with_completed_service) == 0


class TestFrameworkSupplierIdsMany(BaseApplicationTest, FixtureMixin):
    """Test multiple suppliers, multiple services."""

    def test_multiple_services(self):
        framework_id = self.setup_dummy_framework(
            slug='digital-outcomes-and-specialists-2',
            framework_family='digital-outcomes-and-specialists',
        )
        lot = Lot.query.first()
        self.fl_query = {
            'framework_id': framework_id,
            'lot_id': lot.id
        }
        fl = FrameworkLot(**self.fl_query)
        db.session.add(fl)
        db.session.commit()

        # Set u 5 dummy suppliers
        self.setup_dummy_suppliers(5)
        supplier_ids = range(5)
        # 5 sets of statuses for their respective services.
        service_status_choices = [
            ('failed',),
            ('not-submitted',),
            ('failed', 'failed', 'failed', 'not-submitted', 'submitted', 'submitted', 'not-submitted', 'failed'),
            (),
            ('not-submitted', 'submitted', 'not-submitted', 'not-submitted', 'failed')
        ]
        # For the supplier, service_status sets create the services and draft services.
        count = 0
        for supplier_id, service_statuses in zip(supplier_ids, service_status_choices):
            for service_status in service_statuses:
                service_id = str(count) * 10
                count += 1
                self.setup_dummy_service(service_id, supplier_id=supplier_id, **self.fl_query)

                db.session.commit()
                with mock.patch('app.models.main.url_for', autospec=lambda i, **values: 'test.url/test'):
                    ds = DraftService.from_service(Service.query.filter(Service.service_id == service_id).first())
                    ds.status = service_status
                db.session.add(ds)
                db.session.commit()
        # Assert that only those suppliers whose service_status list contains failed and/ or submitted are returned.
        framework = Framework.query.filter(Framework.id == framework_id).first()
        assert sorted(framework.get_supplier_ids_for_completed_service()) == [0, 2, 4]


class TestFrameworkAgreements(BaseApplicationTest, FixtureMixin):
    def setup(self):
        super(TestFrameworkAgreements, self).setup()
        self.setup_dummy_suppliers(1)

        supplier_framework = SupplierFramework(supplier_id=0, framework_id=1)
        db.session.add(supplier_framework)
        db.session.commit()

    def test_supplier_has_to_be_associated_with_a_framework(self):
        # Supplier 0 and SupplierFramework(supplier_id=0, framework_id=1) are created in setup() so these IDs exist
        framework_agreement = FrameworkAgreement(supplier_id=0, framework_id=1)
        db.session.add(framework_agreement)
        db.session.commit()

        assert framework_agreement.id

    def test_supplier_cannot_have_a_framework_agreement_for_a_framework_they_are_not_associated_with(self):
        # SupplierFramework(supplier_id=0, framework_id=2) does not exist so this should fail
        framework_agreement = FrameworkAgreement(supplier_id=0, framework_id=2)
        db.session.add(framework_agreement)

        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_new_framework_agreement_status_is_draft(self):
        framework_agreement = FrameworkAgreement(supplier_id=0, framework_id=1)
        db.session.add(framework_agreement)
        db.session.commit()

        # Check python implementation gives same result as the sql implementation
        assert framework_agreement.status == 'draft'
        assert FrameworkAgreement.query.all()[0].status == 'draft'

    def test_partially_signed_framework_agreement_status_is_draft(self):
        framework_agreement = FrameworkAgreement(
            supplier_id=0,
            framework_id=1,
            signed_agreement_details={'agreement': 'details'},
            signed_agreement_path='path'
        )
        db.session.add(framework_agreement)
        db.session.commit()

        # Check python implementation gives same result as the sql implementation
        assert framework_agreement.status == 'draft'
        assert FrameworkAgreement.query.all()[0].status == 'draft'

    def test_signed_framework_agreement_status_is_signed(self):
        framework_agreement = FrameworkAgreement(
            supplier_id=0,
            framework_id=1,
            signed_agreement_details={'agreement': 'details'},
            signed_agreement_path='path',
            signed_agreement_returned_at=datetime.utcnow()
        )
        db.session.add(framework_agreement)
        db.session.commit()

        # Check python implementation gives same result as the sql implementation
        assert framework_agreement.status == 'signed'
        assert FrameworkAgreement.query.all()[0].status == 'signed'

    def test_on_hold_framework_agreement_status_is_on_hold(self):
        framework_agreement = FrameworkAgreement(
            supplier_id=0,
            framework_id=1,
            signed_agreement_details={'agreement': 'details'},
            signed_agreement_path='path',
            signed_agreement_returned_at=datetime.utcnow(),
            signed_agreement_put_on_hold_at=datetime.utcnow()
        )
        db.session.add(framework_agreement)
        db.session.commit()

        # Check python implementation gives same result as the sql implementation
        assert framework_agreement.status == 'on-hold'
        assert FrameworkAgreement.query.all()[0].status == 'on-hold'

    def test_approved_framework_agreement_status_is_approved(self):
        framework_agreement = FrameworkAgreement(
            supplier_id=0,
            framework_id=1,
            signed_agreement_details={'agreement': 'details'},
            signed_agreement_path='path',
            signed_agreement_returned_at=datetime.utcnow(),
            countersigned_agreement_returned_at=datetime.utcnow()
        )
        db.session.add(framework_agreement)
        db.session.commit()

        # Check python implementation gives same result as the sql implementation
        assert framework_agreement.status == 'approved'
        assert FrameworkAgreement.query.all()[0].status == 'approved'

    def test_countersigned_framework_agreement_status_is_countersigned(self):
        framework_agreement = FrameworkAgreement(
            supplier_id=0,
            framework_id=1,
            signed_agreement_details={'agreement': 'details'},
            signed_agreement_path='path',
            signed_agreement_returned_at=datetime.utcnow(),
            countersigned_agreement_returned_at=datetime.utcnow(),
            countersigned_agreement_path='/path/to/the/countersignedAgreement.pdf'
        )
        db.session.add(framework_agreement)
        db.session.commit()

        # Check python implementation gives same result as the sql implementation
        assert framework_agreement.status == 'countersigned'
        assert FrameworkAgreement.query.all()[0].status == 'countersigned'

    def test_most_recent_signature_time(self):
        framework_agreement = FrameworkAgreement(
            supplier_id=0,
            framework_id=1,
        )
        assert framework_agreement.most_recent_signature_time is None

        framework_agreement.signed_agreement_details = {'agreement': 'details'}
        framework_agreement.signed_agreement_path = '/path/to/the/agreement.pdf'
        framework_agreement.signed_agreement_returned_at = datetime(2016, 9, 10, 11, 12, 0, 0)

        assert framework_agreement.most_recent_signature_time == datetime(2016, 9, 10, 11, 12, 0, 0)

        framework_agreement.countersigned_agreement_path = '/path/to/the/countersignedAgreement.pdf'
        framework_agreement.countersigned_agreement_returned_at = datetime(2016, 10, 11, 10, 12, 0, 0)

        assert framework_agreement.most_recent_signature_time == datetime(2016, 10, 11, 10, 12, 0, 0)

    def test_framework_agreement_serialize_keys_match_api_stub_keys(self):
        # Ensures our dmtestutils.api_model_stubs are kept up to date
        framework_agreement = FrameworkAgreement(supplier_id=0, framework_id=1)
        db.session.add(framework_agreement)
        db.session.commit()

        framework_agreement_stub = FrameworkAgreementStub()
        assert sorted(framework_agreement.serialize().keys()) == sorted(framework_agreement_stub.response().keys())


class TestCurrentFrameworkAgreement(BaseApplicationTest, FixtureMixin):
    """
    Tests the current_framework_agreement property of SupplierFramework objects
    """
    BASE_AGREEMENT_KWARGS = {
        "supplier_id": 0,
        "framework_id": 1,
        "signed_agreement_details": {"agreement": "details"},
        "signed_agreement_path": "path",
    }

    def setup(self):
        super(TestCurrentFrameworkAgreement, self).setup()
        self.setup_dummy_suppliers(1)

        supplier_framework = SupplierFramework(supplier_id=0, framework_id=1)
        db.session.add(supplier_framework)
        db.session.commit()

    def get_supplier_framework(self):
        return SupplierFramework.query.filter(
            SupplierFramework.supplier_id == 0,
            SupplierFramework.framework_id == 1
        ).first()

    def test_current_framework_agreement_with_no_agreements(self):
        supplier_framework = self.get_supplier_framework()
        assert supplier_framework.current_framework_agreement is None

    def test_current_framework_agreement_with_one_draft_only(self):
        db.session.add(FrameworkAgreement(id=5, **self.BASE_AGREEMENT_KWARGS))
        db.session.commit()
        supplier_framework = self.get_supplier_framework()
        assert supplier_framework.current_framework_agreement is None

    def test_current_framework_agreement_with_multiple_drafts(self):
        db.session.add(FrameworkAgreement(id=5, **self.BASE_AGREEMENT_KWARGS))
        db.session.add(FrameworkAgreement(id=6, **self.BASE_AGREEMENT_KWARGS))
        db.session.commit()
        supplier_framework = self.get_supplier_framework()
        assert supplier_framework.current_framework_agreement is None

    def test_current_framework_agreement_with_one_signed(self):
        db.session.add(FrameworkAgreement(
            id=5, signed_agreement_returned_at=datetime(2016, 10, 9, 12, 00, 00), **self.BASE_AGREEMENT_KWARGS)
        )
        supplier_framework = self.get_supplier_framework()
        assert supplier_framework.current_framework_agreement.id == 5

    def test_current_framework_agreement_with_multiple_signed(self):
        db.session.add(FrameworkAgreement(
            id=5, signed_agreement_returned_at=datetime(2016, 10, 9, 12, 00, 00), **self.BASE_AGREEMENT_KWARGS)
        )
        db.session.add(FrameworkAgreement(
            id=6, signed_agreement_returned_at=datetime(2016, 10, 10, 12, 00, 00), **self.BASE_AGREEMENT_KWARGS)
        )
        supplier_framework = self.get_supplier_framework()
        assert supplier_framework.current_framework_agreement.id == 6

    def test_current_framework_agreement_with_signed_and_old_draft_does_not_return_draft(self):
        db.session.add(FrameworkAgreement(id=5, **self.BASE_AGREEMENT_KWARGS))
        db.session.add(FrameworkAgreement(
            id=6, signed_agreement_returned_at=datetime(2016, 10, 10, 12, 00, 00), **self.BASE_AGREEMENT_KWARGS)
        )
        supplier_framework = self.get_supplier_framework()
        assert supplier_framework.current_framework_agreement.id == 6

    def test_current_framework_agreement_with_signed_and_new_draft_does_not_return_draft(self):
        db.session.add(FrameworkAgreement(id=6, **self.BASE_AGREEMENT_KWARGS))
        db.session.add(FrameworkAgreement(
            id=5, signed_agreement_returned_at=datetime(2016, 10, 10, 12, 00, 00), **self.BASE_AGREEMENT_KWARGS)
        )
        supplier_framework = self.get_supplier_framework()
        assert supplier_framework.current_framework_agreement.id == 5

    def test_current_framework_agreement_with_signed_and_new_countersigned(self):
        db.session.add(FrameworkAgreement(
            id=5, signed_agreement_returned_at=datetime(2016, 10, 9, 12, 00, 00), **self.BASE_AGREEMENT_KWARGS)
        )
        db.session.add(FrameworkAgreement(
            id=6,
            signed_agreement_returned_at=datetime(2016, 10, 10, 12, 00, 00),
            countersigned_agreement_returned_at=datetime(2016, 10, 11, 12, 00, 00),
            **self.BASE_AGREEMENT_KWARGS)
        )
        supplier_framework = self.get_supplier_framework()
        assert supplier_framework.current_framework_agreement.id == 6

    def test_current_framework_agreement_with_countersigned_and_new_signed(self):
        db.session.add(FrameworkAgreement(
            id=5, signed_agreement_returned_at=datetime(2016, 10, 11, 12, 00, 00), **self.BASE_AGREEMENT_KWARGS)
        )
        db.session.add(FrameworkAgreement(
            id=6,
            signed_agreement_returned_at=datetime(2016, 10, 9, 12, 00, 00),
            countersigned_agreement_returned_at=datetime(2016, 10, 10, 12, 00, 00),
            **self.BASE_AGREEMENT_KWARGS)
        )
        supplier_framework = self.get_supplier_framework()
        assert supplier_framework.current_framework_agreement.id == 5


class TestArchivedService(BaseApplicationTest, FixtureMixin):

    def setup(self):
        super().setup()

        self.framework_id = \
            self.setup_dummy_framework("g-cloud-11", "g-cloud", "G-Cloud 11", id=111)
        self.supplier_id = self.setup_dummy_suppliers(1)[0]
        self.service_id = "1000000000"
        self.setup_dummy_service(
            data={"serviceName": "Cloud Pies"},
            service_id=self.service_id,
            supplier_id=self.supplier_id,
            status="published",
            lot_id=9,  # cloud-hosting
            framework_id=self.framework_id,
            createdAt="2017-04-07T12:34:00.000000Z",
            updatedAt="2017-05-08T13:24:00.000000Z",
        )

        self.service = Service.query.filter(Service.service_id == self.service_id).first()

    def test_archived_service_serialize_matches_api_stub_response(self):
        # Ensures our dmtestutils.api_model_stubs are kept up to date
        model = ArchivedService.from_service(self.service)
        db.session.add(model)
        db.session.commit()

        stub = ArchivedServiceStub(
            id=model.id,
            service_id=self.service_id,
            framework_slug="g-cloud-11",
            lot="cloud-hosting",
            lot_slug="cloud-hosting",
            lot_name="Cloud hosting",
            service_name="Cloud Pies",
            status="published",
            supplier_id=self.supplier_id,
            supplier_name="Supplier 0",
            created_at="2017-04-07T12:34:00.000000Z",
            updated_at="2017-05-08T13:24:00.000000Z",
        )

        assert model.serialize() == stub.response()
