import json
from app.models import Supplier

form_data = {
    "abn": "50 110 219 460",
    "address_address_line": "1 Commonwealth shmoop",
    "address_country": "Australia",
    "address_postal_code": "8888",
    "address_state": "wa",
    "address_suburb": "wagga",
    "address_supplier_code": 0,
    "contact_email": "brianne@example.com",
    "contact_name": "Anne Example Shmample the third",
    "contact_phone": "0458212000",
    "email": "brianne@example.com",
    "linkedin": "http://linkedin.com/yo/laland",
    "name": "Apple Inc Pty Ltd",
    "phone": "0458212000",
    "representative": "Anne Example Shmample the third",
    "summary": "An example apple company. zs",
    "website": "https://example.com/yo/yo/d"
}


def test_require_supplier_role_for_profile(app, supplier_user, client, mocker):
    code = supplier_user.supplier_code
    response = client.post(
        '/2/suppliers/{}'.format(code),
        data=json.dumps(form_data),
        content_type='application/json')

    assert response.status_code == 401


def test_update_supplier_profile(app, supplier_user, client, mocker):
    code = supplier_user.supplier_code
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': supplier_user.email_address, 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    assert not hasattr(supplier_user, 'addresses')
    assert not hasattr(supplier_user, 'contacts')

    form_data['code'] = code
    form_data['id'] = supplier_user.id

    response = client.post(
        '/2/suppliers/{}'.format(code),
        data=json.dumps(form_data),
        content_type='application/json')

    assert response.status_code == 200

    supplier_data = json.loads(response.data)

    print supplier_data
    updated_supplier_instance = Supplier.query.filter(
        Supplier.code == supplier_data.get('code')).first()

    assert hasattr(updated_supplier_instance, 'addresses')
    assert hasattr(updated_supplier_instance, 'contacts')


def test_supplier_services(client, supplier_user, service_type_prices):
    code = supplier_user.supplier_code
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.get('/2/suppliers/{}'.format(code))
    assert response.status_code == 200

    supplier = json.loads(response.data)
    assert supplier['services'] == [{'id': 1, 'name': 'Service1', 'subCategories': [{'id': 1, 'name': ''}]}]


def test_list_suppliers(client, users, service_type_prices):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.get('/2/suppliers')
    assert response.status_code == 200
    assert json.loads(response.data) == {'categories': [{'suppliers': [{'code': 1, 'name': 'Test Supplier1'}],
                                                         'name': 'Medical'},
                                                        {'name': 'Rehabilitation',
                                                         'suppliers': [{'code': 2, 'name': 'Test Supplier2'}]}]}


def test_search_suppliers_success(client, suppliers):
    response = client.get('/2/suppliers/search?keyword=test')
    assert response.status_code == 200
    assert json.loads(response.data) == {'sellers': [
        {
            "code": 1,
            "name": "Test Supplier1",
            "panel": False,
            "sme": False
        },
        {
            "code": 2,
            "name": "Test Supplier2",
            "panel": False,
            "sme": False
        },
        {
            "code": 3,
            "name": "Test Supplier3",
            "panel": False,
            "sme": False
        },
        {
            "code": 4,
            "name": "Test Supplier4",
            "panel": False,
            "sme": False
        },
        {
            "code": 5,
            "name": "Test Supplier5",
            "panel": False,
            "sme": False
        }
    ]}


def test_search_suppliers_bad_request_no_keyword(client):
    response = client.get('/2/suppliers/search')
    assert response.status_code == 400
