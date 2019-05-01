from __future__ import absolute_import

import pendulum
import pytest
from faker import Faker
from sqlbag import temporary_database

from app import create_app, encryption
from app.models import (Agency, Application, Assessment, Brief, BriefResponse,
                        BriefUser, Contact, Domain, Framework, FrameworkLot,
                        Lot, Supplier, SupplierDomain, SupplierFramework, User,
                        UserFramework, CaseStudy, db, utcnow)
from migrations import load_from_app_model, load_test_fixtures
from tests.app.helpers import (COMPLETE_DIGITAL_SPECIALISTS_BRIEF,
                               WSGIApplicationWithEnvironment)

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

        db.session.add(Agency(
            id=3,
            name='Another Test Agency',
            domain='asdf.com.au',
            category='Commonwealth',
            whitelisted=True
        ))

        db.session.commit()
        yield Agency.query.all()


@pytest.fixture()
def suppliers(app, request):
    params = request.param if hasattr(request, 'param') else {}
    framework_slug = params['framework_slug'] if 'framework_slug' in params else 'digital-marketplace'
    with app.app_context():
        framework = Framework.query.filter(Framework.slug == framework_slug).first()
        for i in range(1, 6):
            db.session.add(Supplier(
                abn=i,
                code=(i),
                name='Test Supplier{}'.format(i),
                contacts=[Contact(name='auth rep', email='auth@rep.com')],
                data={
                    'contact_email': 'test{}@supplier.com'.format(i),
                    'contact_phone': '123'
                }
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
def case_studies(app, request, domains, suppliers, supplier_domains):
    params = request.param if hasattr(request, 'param') else {}
    status = params['status'] if 'status' in params else 'approved'
    supplier_code = params['supplier_code'] if 'supplier_code' in params else suppliers[0].code
    with app.app_context():
        for domain in domains:
            case_study = CaseStudy.query.order_by(CaseStudy.id.desc()).first()
            id = case_study.id + 1 if case_study else 1
            db.session.add(CaseStudy(
                id=id,
                data={'service': domain.name, 'title': 'TEST'},
                supplier_code=supplier_code,
                status=status
            ))
            db.session.flush()
        db.session.commit()
        yield CaseStudy.query.all()


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
    framework_slug = params['framework_slug'] if 'framework_slug' in params else 'digital-marketplace'
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
def admin_users(app, request):
    with app.app_context():
        db.session.add(User(
            id=7,
            email_address='testadmin@digital.gov.au',
            name=fake.name(),
            password=encryption.hashpw('testpassword'),
            active=True,
            role='admin',
            password_changed_at=utcnow()
        ))

        db.session.commit()
        yield User.query.filter(User.role == 'admin').all()


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
        framework = Framework.query.filter(Framework.slug == 'digital-marketplace').first()
        db.session.add(UserFramework(user_id=id, framework_id=framework.id))
        db.session.commit()
        yield User.query.get(id)


@pytest.fixture()
def applicant_user(app, request):
    with app.app_context():
        user = User.query.order_by(User.id.desc()).first()
        id = user.id + 1 if user else 1
        db.session.add(User(
            id=id,
            email_address='j@examplecompany.biz',
            name=fake.name(),
            password=encryption.hashpw('testpassword'),
            active=True,
            role='applicant',
            supplier_code=None,
            password_changed_at=utcnow()
        ))
        db.session.commit()
        framework = Framework.query.filter(Framework.slug == 'digital-marketplace').first()
        db.session.add(UserFramework(user_id=id, framework_id=framework.id))
        db.session.commit()
        yield User.query.get(id)


@pytest.fixture()
def buyer_user(app, request):
    with app.app_context():
        user = User.query.order_by(User.id.desc()).first()
        id = user.id + 1 if user else 1
        db.session.add(User(
            id=id,
            email_address='me@digital.gov.au',
            name=fake.name(),
            password=encryption.hashpw('test'),
            active=True,
            role='buyer',
            password_changed_at=utcnow()
        ))
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
    lot_slug = params['lot_slug'] if 'lot_slug' in params else 'digital-professionals'
    framework_slug = params['framework_slug'] if 'framework_slug' in params else 'digital-service-professionals'
    with app.app_context():
        for i in range(1, 6):
            db.session.add(Brief(
                id=i,
                data=data,
                framework=Framework.query.filter(Framework.slug == framework_slug).first(),
                lot=Lot.query.filter(Lot.slug == lot_slug).first(),
                users=users,
                published_at=published_at,
                withdrawn_at=None
            ))
            db.session.flush()

        db.session.commit()
        yield Brief.query.all()


@pytest.fixture()
def brief_responses(app, request, briefs, supplier_user):
    params = request.param if hasattr(request, 'param') else {}
    data = params['data'] if 'data' in params else {}
    with app.app_context():
        db.session.add(BriefResponse(
            id=1,
            brief_id=1,
            supplier_code=supplier_user.supplier_code,
            data=data
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
def rfx_brief(client, app, request, buyer_user):
    params = request.param if hasattr(request, 'param') else {}
    data = params['data'] if 'data' in params else {'title': 'RFX TEST'}
    with app.app_context():
        framework = Framework.query.filter(Framework.slug == 'digital-marketplace').first()
        framework.status = 'live'
        db.session.add(framework)
        db.session.commit()
        db.session.add(Brief(
            id=1,
            data=data,
            framework=Framework.query.filter(Framework.slug == "digital-marketplace").first(),
            lot=Lot.query.filter(Lot.slug == 'rfx').first(),
            users=[buyer_user]
        ))
        db.session.commit()
        yield Brief.query.get(1)


@pytest.fixture()
def atm_brief(client, app, request, buyer_user):
    params = request.param if hasattr(request, 'param') else {}
    data = params['data'] if 'data' in params else {'title': 'ATM TEST'}
    with app.app_context():
        framework = Framework.query.filter(Framework.slug == 'digital-marketplace').first()
        framework.status = 'live'
        db.session.add(framework)
        db.session.commit()
        db.session.add(Brief(
            id=1,
            data=data,
            framework=Framework.query.filter(Framework.slug == "digital-marketplace").first(),
            lot=Lot.query.filter(Lot.slug == 'atm').first(),
            users=[buyer_user]
        ))
        db.session.commit()
        yield Brief.query.get(1)
