from __future__ import absolute_import

import pytest

from app import create_app
from app.models import db, utcnow, Supplier, SupplierDomain, User, Brief, \
    Framework, Lot, Domain, Assessment
from tests.app.helpers import COMPLETE_DIGITAL_SPECIALISTS_BRIEF, WSGIApplicationWithEnvironment

from sqlbag import temporary_database
from faker import Faker

from migrations import \
    load_from_app_model, load_test_fixtures

fake = Faker()


@pytest.fixture(autouse=True)
def db_initialization(request):
    from config import configs

    with temporary_database() as dburi:
        test_config = configs['test']
        test_config.SQLALCHEMY_DATABASE_URI = dburi

        load_from_app_model(dburi)
        load_test_fixtures(dburi)

        yield


def setup_authorization(app):
    valid_token = 'valid-token'
    app.wsgi_app = WSGIApplicationWithEnvironment(
        app.wsgi_app,
        HTTP_AUTHORIZATION='Bearer {}'.format(valid_token))
    app.config['DM_API_AUTH_TOKENS'] = valid_token


@pytest.fixture()
def app(request):
    app = create_app('test')
    app.config['SERVER_NAME'] = 'localhost'
    setup_authorization(app)
    yield app


@pytest.fixture()
def client(app):
    yield app.test_client()


@pytest.fixture()
def suppliers(app, request):
    with app.app_context():
        for i in range(1, 6):
            db.session.add(Supplier(
                code=(i),
                name=fake.name()
            ))

            db.session.flush()

        db.session.commit()
        yield Supplier.query.all()


@pytest.fixture()
def supplier_domains(app, request, suppliers):
    with app.app_context():
        for s in suppliers:
            for i in range(1, 6):
                db.session.add(SupplierDomain(
                    supplier_id=s.id,
                    domain_id=i
                ))

                db.session.flush()

        db.session.commit()
        yield SupplierDomain.query.all()


@pytest.fixture()
def users(app, request):
    with app.app_context():
        for i in range(1, 6):
            db.session.add(User(
                id=i,
                email_address='{}{}@digital.gov.au'.format(fake.first_name(), i),
                name=fake.name(),
                password=fake.password(),
                active=True,
                role='buyer',
                password_changed_at=utcnow()
            ))
            db.session.flush()

        db.session.commit()
        yield User.query.all()


@pytest.fixture()
def briefs(app, request, users):
    with app.app_context():
        for i in range(1, 6):
            db.session.add(Brief(
                id=i,
                data=COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy(),
                framework=Framework.query.filter(Framework.slug == "digital-outcomes-and-specialists").first(),
                lot=Lot.query.filter(Lot.slug == 'digital-specialists').first(),
                users=users,
                published_at=utcnow(),
                withdrawn_at=None
            ))
            db.session.flush()

        db.session.commit()
        yield Brief.query.all()


@pytest.fixture()
def domains(app, request):
    with app.app_context():
        yield Domain.query.all()


@pytest.fixture()
def assessments(app, request, supplier_domains, briefs):
    with app.app_context():
        for i in range(1, 6):
            supplier_domain = supplier_domains[i]
            db.session.add(Assessment(
                supplier_domain=supplier_domain,
                briefs=briefs
            ))
            db.session.flush()

        db.session.commit()
        yield Assessment.query.all()
