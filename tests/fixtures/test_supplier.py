import json
import pendulum
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
    response = client.post(
        '/2/supplier',
        data=json.dumps(form_data),
        content_type='application/json')

    assert response.status_code == 401


def test_update_supplier_profile(app, supplier_user, client, mocker):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': supplier_user.email_address, 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    assert not hasattr(supplier_user, 'addresses')
    assert not hasattr(supplier_user, 'contacts')

    form_data['code'] = supplier_user.supplier_code
    form_data['id'] = supplier_user.id

    response = client.post(
        '/2/supplier',
        data=json.dumps(form_data),
        content_type='application/json')

    assert response.status_code == 200

    supplier_data = json.loads(response.data)

    updated_supplier_instance = Supplier.query.filter(
        Supplier.code == supplier_data['user'].get('code')).first()

    assert hasattr(updated_supplier_instance, 'addresses')
    assert hasattr(updated_supplier_instance, 'contacts')


def test_supplier_services(client, supplier_user, service_type_prices):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.get('/2/supplier/services')
    assert response.status_code == 200

    services = json.loads(response.data)
    assert services == {'services': [{'id': 1, 'name': 'Service1', 'subCategories': [{'id': 1, 'name': ''}]}],
                        'supplier': {'abn': '1', 'email': 'auth@rep.com', 'contact': 'auth rep',
                                     'name': 'Test Supplier1'}}


def test_supplier_service_prices(client, supplier_user, service_type_prices):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.get('/2/supplier/services/1/categories/1/prices')
    assert response.status_code == 200

    price = json.loads(response.data)['prices'][0]
    assert price['capPrice'] == '321.56'
    assert price['price'] == '200.50'


def test_supplier_price_update(client, supplier_user, service_type_prices):
    pendulum.set_formatter('alternative')
    id = service_type_prices[0].id
    date_from = service_type_prices[0].date_from
    existing_price = '{:1,.2f}'.format(service_type_prices[0].price)
    start_date = pendulum.Date.tomorrow()
    end_date = pendulum.Date.tomorrow().add(months=1)
    new_price = 246.96

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.post(
        '/2/supplier/prices',
        data=json.dumps({'price': []}),
        content_type='application/json')
    assert response.status_code == 400
    assert json.loads(response.data)['message'] == '\'prices\' is a required property'

    response = client.post(
        '/2/supplier/prices',
        data=json.dumps({'prices': [{'id': id, 'price': new_price,
                                     'startDate': 'invalid start',
                                     'endDate': str(end_date)}]}),
        content_type='application/json')
    assert response.status_code == 400
    assert json.loads(response.data)['message'] == 'Invalid date string: invalid start'

    response = client.post(
        '/2/supplier/prices',
        data=json.dumps({'prices': [{'id': id, 'price': new_price,
                                     'startDate': str(pendulum.Date.today()),
                                     'endDate': str(end_date)}]}),
        content_type='application/json')
    assert response.status_code == 400
    assert json.loads(response.data)['message'] == 'startDate must be in the future: {}'.format(pendulum.Date.today())

    response = client.post(
        '/2/supplier/prices',
        data=json.dumps({'prices': [{'id': id, 'price': new_price,
                                     'startDate': str(start_date),
                                     'endDate': str(pendulum.Date.today())}]}),
        content_type='application/json')
    assert response.status_code == 400
    assert json.loads(response.data)['message'] == 'endDate must be after startDate: {}'.format(pendulum.Date.today())

    response = client.post(
        '/2/supplier/prices',
        data=json.dumps({'prices': [{'id': id, 'price': 1000,
                                     'startDate': str(start_date),
                                     'endDate': str(end_date)}]}),
        content_type='application/json')
    assert response.status_code == 400
    assert json.loads(response.data)['message'] == 'price must be less than capPrice: 1000'

    response = client.post(
        '/2/supplier/prices',
        data=json.dumps({'prices': [{'id': id, 'price': new_price,
                                     'startDate': str(start_date),
                                     'endDate': str(end_date)}]}),
        content_type='application/json')
    assert response.status_code == 200

    prices = json.loads(response.data)['prices'][0]
    assert prices[0]['startDate'] == pendulum.parse(str(date_from)).format('DD/MM/YYYY')
    assert prices[0]['endDate'] == start_date.subtract(days=1).format('DD/MM/YYYY')
    assert prices[0]['price'] == existing_price
    assert prices[1]['startDate'] == start_date.format('DD/MM/YYYY')
    assert prices[1]['endDate'] == end_date.format('DD/MM/YYYY')
    assert prices[1]['price'] == str(new_price)
    assert prices[2]['startDate'] == end_date.add(days=1).format('DD/MM/YYYY')
    assert prices[2]['endDate'] == pendulum.create(2050, 1, 1).format('DD/MM/YYYY')
    assert prices[2]['price'] == existing_price


def test_list_suppliers(client, users, service_type_prices):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.get('/2/suppliers')
    assert response.status_code == 200
    assert json.loads(response.data) == {'categories': [{'suppliers': [{'code': 1, 'name': 'Test Supplier1'}],
                                                         'name': 'Medical'}]}
