import json
from app.models import Supplier, SupplierDomain, CaseStudy, db
import pytest


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


@pytest.mark.parametrize('suppliers', [{'framework_slug': 'digital-marketplace'}], indirect=True)
def test_search_suppliers_success(client, suppliers, domains, supplier_domains):
    response = client.get('/2/suppliers/search?keyword=test')
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


def test_search_suppliers_bad_request_no_keyword(client):
    response = client.get('/2/suppliers/search')
    assert response.status_code == 400
