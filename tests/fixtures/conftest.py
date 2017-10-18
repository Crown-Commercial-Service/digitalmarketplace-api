from __future__ import absolute_import

import pytest

from app import create_app
from app.models import db, utcnow, Supplier, SupplierDomain, User, Brief, \
    Framework, Lot, Domain, Assessment, Application, Region, ServiceType, ServiceTypePrice, Service, ServiceSubType
from tests.app.helpers import COMPLETE_DIGITAL_SPECIALISTS_BRIEF, WSGIApplicationWithEnvironment

from sqlbag import temporary_database
from faker import Faker

from migrations import \
    load_from_app_model, load_test_fixtures

from flask_login import login_user
from dmutils.user import User as LoginUser
from app import encryption

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


@pytest.fixture()
def app(request):
    app = create_app('test')
    app.config['SERVER_NAME'] = 'localhost'
    app.config['CSRF_ENABLED'] = False
    yield app


@pytest.fixture()
def bearer(app):
    valid_token = 'valid-token'
    app.wsgi_app = WSGIApplicationWithEnvironment(
        app.wsgi_app,
        HTTP_AUTHORIZATION='Bearer {}'.format(valid_token))
    app.config['DM_API_AUTH_TOKENS'] = valid_token


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
def applications(app, request):
    with app.app_context():
        for i in range(1, 6):
            db.session.add(Application(
                id=(i),
            ))

            db.session.flush()

        db.session.commit()
        yield Application.query.all()


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

        db.session.add(User(
            id=7,
            email_address='test@digital.gov.au',
            name=fake.name(),
            password=encryption.hashpw('testpassword'),
            active=True,
            role='buyer',
            password_changed_at=utcnow()
        ))
        db.session.flush()

        db.session.commit()
        yield User.query.all()


@pytest.fixture()
def supplier_user(app, request, suppliers):
    with app.app_context():
        db.session.add(User(
            id=1,
            email_address='j@examplecompany.biz',
            name=fake.name(),
            password=encryption.hashpw('testpassword'),
            active=True,
            role='supplier',
            supplier_code=suppliers[0].code,
            password_changed_at=utcnow()
        ))
        db.session.commit()
        yield User.query.first()


@pytest.fixture()
def application_user(app, request, applications):
    with app.app_context():
        db.session.add(User(
            id=1,
            email_address='don@don.com',
            name=fake.name(),
            password=fake.password(),
            active=True,
            role='applicant',
            application_id=applications[0].id,
            password_changed_at=utcnow()
        ))
        db.session.commit()
        yield User.query.first()


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


@pytest.fixture()
def regions(app, request):
    with app.app_context():
        db.session.add(Region(
            name='Metro',
            state='NSW'
        ))
        db.session.add(Region(
            name='Remote',
            state='NSW'
        ))
        db.session.add(Region(
            name='Metro',
            state='QLD'
        ))

        db.session.commit()
        yield Region.query.all()


@pytest.fixture()
def services(app, request):
    with app.app_context():
        db.session.add(ServiceType(
            name='Service1',
            fee_type='Hourly',
            category_id=10,
            framework_id=8,
            lot_id=11
        ))
        db.session.add(ServiceType(
            name='Service2',
            fee_type='Fixed',
            category_id=11,
            framework_id=8,
            lot_id=11
        ))

        db.session.commit()
        yield ServiceType.query.all()


@pytest.fixture()
def service_type_prices(app, request, regions, services, suppliers):
    with app.app_context():
        db.session.add(ServiceSubType(
            name='SubType1'
        ))
        db.session.flush()

        db.session.add(ServiceTypePrice(
            service_type_id=1,
            region_id=1,
            supplier_code=1,
            price=100.50
        ))
        db.session.add(ServiceTypePrice(
            service_type_id=2,
            region_id=2,
            sub_service_id=1,
            supplier_code=1,
            price=200.90
        ))

        db.session.commit()
        yield ServiceTypePrice.query.all()
