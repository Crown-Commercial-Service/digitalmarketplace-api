import json
from app.models import Brief, User, Supplier, SupplierDomain, CaseStudy, db
from app.api.services import frameworks_service, lots_service
import pytest
import pendulum


@pytest.fixture()
def briefs(app, request, users):
    with app.app_context():
        now = pendulum.now('utc')
        framework = frameworks_service.find(slug='digital-marketplace').one_or_none()
        atm_lot = lots_service.find(slug='atm').one_or_none()
        rfx_lot = lots_service.find(slug='rfx').one_or_none()
        specialist_lot = lots_service.find(slug='specialist').one_or_none()
        training_lot = lots_service.find(slug='training2').one_or_none()

        db.session.add(
            Brief(
                id=1,
                data={},
                framework=framework,
                lot=atm_lot,
                users=users,
                published_at=now.subtract(days=2),
                withdrawn_at=None
            )
        )

        db.session.add(
            Brief(
                id=2,
                data={},
                framework=framework,
                lot=rfx_lot,
                users=users,
                published_at=now.subtract(days=2),
                withdrawn_at=None
            )
        )

        db.session.add(
            Brief(
                id=3,
                data={},
                framework=framework,
                lot=specialist_lot,
                users=users,
                published_at=now.subtract(days=2),
                withdrawn_at=None
            )
        )

        db.session.add(
            Brief(
                id=4,
                data={},
                framework=framework,
                lot=training_lot,
                users=users,
                published_at=now.subtract(days=2),
                withdrawn_at=None
            )
        )

        db.session.commit()
        yield db.session.query(Brief).all()


@pytest.fixture()
def supplier_domains(app, request, suppliers):
    with app.app_context():
        for s in suppliers:
            for i in range(1, 6):
                supplier_domain = SupplierDomain(
                    supplier_id=s.id,
                    domain_id=i,
                    status='assessed',
                    price_status='approved'
                )
                db.session.add(supplier_domain)
                db.session.flush()

                db.session.add(CaseStudy(
                    data={'service': supplier_domain.domain.name},
                    status='approved',
                    supplier_code=s.code
                ))

        db.session.commit()
        yield SupplierDomain.query.all()


@pytest.fixture()
def users(app):
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


@pytest.mark.parametrize('suppliers', [{'framework_slug': 'digital-marketplace'}], indirect=True)
def test_search_suppliers_success(client, briefs, suppliers, domains, supplier_domains):
    response = client.get('/2/suppliers/search?keyword=test&briefId=3')
    assert response.status_code == 200
    assert json.loads(response.data) == {'sellers': [
        {
            "code": 1,
            "name": "Test Supplier1"
        },
        {
            "code": 2,
            "name": "Test Supplier2"
        },
        {
            "code": 3,
            "name": "Test Supplier3"
        },
        {
            "code": 4,
            "name": "Test Supplier4"
        },
        {
            "code": 5,
            "name": "Test Supplier5"
        }
    ]}


def test_search_suppliers_bad_request_no_keyword(client, briefs):
    response = client.get('/2/suppliers/search?briefId=3')
    assert response.status_code == 400
