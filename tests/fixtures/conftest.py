from __future__ import absolute_import

import pytest
import pendulum

from app import create_app
from app.models import db, utcnow, Agency, Contact, Supplier, SupplierDomain, User, Brief, ServiceTypePriceCeiling,\
    Framework, Lot, Domain, Assessment, Application, Region, ServiceType, ServiceTypePrice, ServiceSubType,\
    SupplierFramework, UserFramework, BriefResponse, BriefUser
from tests.app.helpers import COMPLETE_DIGITAL_SPECIALISTS_BRIEF, WSGIApplicationWithEnvironment

from sqlbag import temporary_database
from faker import Faker

from migrations import \
    load_from_app_model, load_test_fixtures

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
def agencies(app, request):
    with app.app_context():
        db.session.add(Agency(
            id=1,
            name='Digital Transformation Agency',
            domain='digital.gov.au',
            category='Commonwealth',
            whitelisted=True
        ))

        db.session.add(Agency(
            id=2,
            name='Test Agency',
            domain='test.gov.au',
            category='Commonwealth',
            whitelisted=True
        ))

        db.session.commit()
        yield Agency.query.all()


@pytest.fixture()
def suppliers(app, request):
    params = request.param if hasattr(request, 'param') else {}
    framework_slug = params['framework_slug'] if 'framework_slug' in params else 'orams'
    with app.app_context():
        framework = Framework.query.filter(Framework.slug == framework_slug).first()
        for i in range(1, 6):
            db.session.add(Supplier(
                abn=i,
                code=(i),
                name='Test Supplier{}'.format(i),
                contacts=[Contact(name='auth rep', email='auth@rep.com')],
                data={'contact_email': 'test{}@supplier.com'.format(i)}
            ))

            db.session.flush()

            db.session.add(SupplierFramework(supplier_code=i, framework_id=framework.id))

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
    params = request.param if hasattr(request, 'param') else {}
    user_role = params['user_role'] if 'user_role' in params else 'buyer'
    email_domain = params['email_domain'] if 'email_domain' in params else 'digital.gov.au'
    framework_slug = params['framework_slug'] if 'framework_slug' in params else 'orams'
    with app.app_context():
        for i in range(1, 6):
            new_user = User(
                id=i,
                email_address='{}{}@{}'.format(fake.first_name(), i, email_domain),
                name=fake.name(),
                password=fake.password(),
                active=True,
                role=user_role,
                password_changed_at=utcnow()
            )
            if user_role == 'supplier':
                new_user.supplier_code = i
            db.session.add(new_user)
            db.session.flush()
            framework = Framework.query.filter(Framework.slug == framework_slug).first()
            db.session.add(UserFramework(user_id=i, framework_id=framework.id))

        if user_role == 'buyer':
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
            db.session.add(UserFramework(user_id=7, framework_id=framework.id))

        db.session.commit()
        yield User.query.filter(User.role == user_role).all()


@pytest.fixture()
def supplier_user(app, request, suppliers):
    with app.app_context():
        user = User.query.order_by(User.id.desc()).first()
        id = user.id + 1 if user else 1
        db.session.add(User(
            id=id,
            email_address='j@examplecompany.biz',
            name=fake.name(),
            password=encryption.hashpw('testpassword'),
            active=True,
            role='supplier',
            supplier_code=suppliers[0].code,
            password_changed_at=utcnow()
        ))
        db.session.commit()
        framework = Framework.query.filter(Framework.slug == "orams").first()
        db.session.add(UserFramework(user_id=id, framework_id=framework.id))
        db.session.commit()
        yield User.query.get(id)


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
    params = request.param if hasattr(request, 'param') else {}
    published_at = pendulum.parse(params['published_at']) if 'published_at' in params else utcnow()
    data = params['data'] if 'data' in params else COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy()
    with app.app_context():
        for i in range(1, 6):
            db.session.add(Brief(
                id=i,
                data=data,
                framework=Framework.query.filter(Framework.slug == "digital-service-professionals").first(),
                lot=Lot.query.filter(Lot.slug == 'digital-professionals').first(),
                users=users,
                published_at=published_at,
                withdrawn_at=None
            ))
            db.session.flush()

        db.session.commit()
        yield Brief.query.all()


@pytest.fixture()
def brief_responses(app, request, briefs, supplier_user):
    with app.app_context():
        db.session.add(BriefResponse(
            id=1,
            brief_id=1,
            supplier_code=supplier_user.supplier_code,
            data={}
        ))

        db.session.commit()
        yield BriefResponse.query.all()


@pytest.fixture()
def brief_users(app):
    with app.app_context():
        yield BriefUser.query.all()


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
            id=1,
            name=''
        ))
        db.session.add(ServiceSubType(
            id=2,
            name='SubType1'
        ))
        db.session.flush()

        db.session.add(ServiceTypePriceCeiling(
            service_type_id=1,
            sub_service_id=1,
            region_id=1,
            supplier_code=1,
            price=321.56
        ))
        db.session.flush()

        db.session.add(ServiceTypePrice(
            service_type_id=1,
            sub_service_id=1,
            region_id=1,
            supplier_code=1,
            service_type_price_ceiling_id=1,
            price=210.60,
            date_from='1/1/2016',
            date_to=pendulum.Date.today()
        ))
        db.session.add(ServiceTypePrice(
            service_type_id=1,
            sub_service_id=1,
            region_id=1,
            supplier_code=1,
            service_type_price_ceiling_id=1,
            price=200.50,
            date_from='1/1/2016',
            date_to=pendulum.Date.today()
        ))
        db.session.add(ServiceTypePrice(
            service_type_id=1,
            sub_service_id=1,
            region_id=1,
            supplier_code=1,
            service_type_price_ceiling_id=1,
            price=100.50,
            date_from=pendulum.Date.tomorrow(),
            date_to='1/1/2050'
        ))
        db.session.add(ServiceTypePrice(
            service_type_id=2,
            sub_service_id=2,
            region_id=2,
            supplier_code=2,
            service_type_price_ceiling_id=1,
            price=200.90,
            date_from=pendulum.Date.today(),
            date_to='1/1/2050'
        ))

        db.session.commit()
        yield ServiceTypePrice.query.all()
