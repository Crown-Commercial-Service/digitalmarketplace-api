from datetime import datetime

import mock
import pytest
from nose.tools import assert_equal, assert_raises
from sqlalchemy.exc import IntegrityError

from app import db, create_app
from app.models import (
    User, Framework, Service,
    Supplier, SupplierFramework,
    Brief, BriefResponse,
    ValidationError,
)

from .helpers import BaseApplicationTest


def test_should_not_return_password_on_user():
    app = create_app('test')
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

    with app.app_context():
        assert_equal(user.serialize()['emailAddress'], "email@digital.gov.uk")
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

        with self.app.app_context():
            db.session.add(brief)
            db.session.commit()

            assert brief.status == 'draft'

    def test_status_must_be_valid(self):
        with pytest.raises(ValidationError):
            brief = Brief(data={}, framework=self.framework, lot=self.lot)

            brief.status = 'invalid'

    def test_publishing_a_brief_sets_published_at(self):
        with self.app.app_context():
            brief = Brief(data={}, framework=self.framework, lot=self.lot)
            db.session.add(brief)
            db.session.commit()

            assert brief.published_at is None

            brief.status = 'live'

            assert isinstance(brief.published_at, datetime)

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
            self.supplier = Supplier.query.filter(Supplier.supplier_id == 0).first()

    def test_create_a_new_brief_response(self):
        with self.app.app_context():
            brief_response = BriefResponse(data={}, brief=self.brief, supplier=self.supplier)
            db.session.add(brief_response)
            db.session.commit()

            assert brief_response.id is not None
            assert brief_response.supplier_id == 0
            assert brief_response.brief_id == self.brief.id
            assert isinstance(brief_response.created_at, datetime)
            assert brief_response.data == {}

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
                    'supplierId': 0,
                    'supplierName': 'Supplier 0',
                    'createdAt': mock.ANY,
                    'foo': 'bar',
                    'links': {
                        'self': (('.get_brief_response',), {'brief_response_id': brief_response.id}),
                        'brief': (('.get_brief',), {'brief_id': self.brief.id}),
                        'supplier': (('.get_supplier',), {'supplier_id': 0}),
                    }
                }


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
            assert(all(s.framework.status == 'live' for s in services))

    def test_lot_must_be_associated_to_the_framework(self):
        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            self.setup_dummy_service(
                service_id='10000000001',
                supplier_id=0,
                framework_id=5,  # Digital Outcomes and Specialists
                lot_id=1)  # SaaS
            with pytest.raises(IntegrityError) as excinfo:
                db.session.commit()

            assert 'not present in table "framework_lots"' in "{}".format(excinfo.value)

    def test_default_ordering(self):
        def add_service(service_id, framework_id, lot_id, service_name):
            self.setup_dummy_service(
                service_id=service_id,
                supplier_id=0,
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
                supplier_id=0,
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
