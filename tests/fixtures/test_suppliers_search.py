import json
from app.models import Supplier
import pytest


@pytest.mark.parametrize('suppliers', [{'framework_slug': 'digital-marketplace'}], indirect=True)
def test_search_suppliers_success(client, suppliers):
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
