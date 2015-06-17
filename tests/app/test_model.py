from datetime import datetime

from nose.tools import assert_equal, assert_raises
from sqlalchemy.exc import DataError

from app import db, create_app
from app.models import User, Framework, Service
from .helpers import BaseApplicationTest


def test_should_not_return_password_on_user():
    now = datetime.now()
    user = User(
        email_address='email',
        name='name',
        role='buyer',
        password='password',
        active=True,
        locked=False,
        created_at=now,
        updated_at=now,
        password_changed_at=now
    )

    assert_equal(user.serialize()['emailAddress'], "email")
    assert_equal(user.serialize()['name'], "name")
    assert_equal(user.serialize()['role'], "buyer")
    assert_equal('password' in user.serialize(), False)


def test_framework_should_not_accept_invalid_status():
    app = create_app('test')
    with app.app_context(), assert_raises(DataError):
        f = Framework(
            name='foo',
            framework='gcloud',
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
                framework='gcloud',
                status=status,
            )
            db.session.add(f)
            db.session.commit()


class TestServices(BaseApplicationTest):
    def test_framework_is_live_only_returns_live_frameworks(self):
        with self.app.app_context():
            self.setup_dummy_service(
                service_id='999',
                status='published',
                framework_id=self.setup_dummy_framework())
            self.setup_dummy_services_including_unpublished(1)

            services = Service.query.framework_is_live()

            assert_equal(Service.query.count(), 4)
            assert_equal(services.count(), 3)
            assert(all(s.framework.status == 'live' for s in services))

    def test_default_ordering(self):
        def add_service(service_id, framework_id, lot, service_name):
            self.setup_dummy_service(
                service_id=service_id,
                supplier_id=0,
                framework_id=framework_id,
                data={'lot': lot, 'serviceName': service_name})

        with self.app.app_context():
            self.setup_dummy_suppliers(1)
            add_service('990', 3, 'zzz', 'zzz')
            add_service('991', 3, 'zzz', 'aaa')
            add_service('992', 3, 'aaa', 'zzz')
            add_service('993', 1, 'zzz', 'zzz')
            db.session.commit()

            services = Service.query.default_order()

            assert_equal(
                [s.service_id for s in services],
                ['993', '992', '991', '990'])

    def test_has_statuses(self):
        with self.app.app_context():
            self.setup_dummy_services_including_unpublished(1)

            services = Service.query.has_statuses('published')

            assert_equal(services.count(), 1)

    def test_has_statuses_should_accept_multiple_statuses(self):
        with self.app.app_context():
            self.setup_dummy_services_including_unpublished(1)

            services = Service.query.has_statuses('published', 'disabled')

            assert_equal(services.count(), 2)
