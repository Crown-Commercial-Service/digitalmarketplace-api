import json
import pendulum
from nose.tools import assert_equal
from app.models import Supplier

form_data = {
    "abn": "50 110 219 460",
    "acn": None,
    "address_address_line": "1 Commonwealth shmoop",
    "address_country": "Australia",
    "address_links": {
        "self": "http://localhost:8000/addresses/2565",
        "supplier": "http://localhost:8000/suppliers/0"
    },
    "address_postal_code": "8888",
    "address_state": "wa",
    "address_suburb": "wagga",
    "address_supplier_code": 0,
    "application_id": 2,
    "case_studies": [],
    "case_study_ids": [],
    "contact_contactFor": None,
    "contact_contact_for": None,
    "contact_email": "brianne@example.com",
    "contact_fax": None,
    "contact_links": {
        "self": "http://localhost:8000/contacts/2655"
    },
    "contact_name": "Anne Example Shmample the third",
    "contact_phone": "0458212000",
    "contact_role": None,
    "creationTime": "2016-10-04T04:33:28.468193+00:00",
    "creation_time": "2016-10-04T04:33:28.468193+00:00",
    "description": None,
    "domains": {
        "assessed": [],
        "legacy": [],
        "unassessed": []
    },
    "email": "brianne@example.com",
    "extraLinks": [],
    "extra_links": [],
    "frameworks": [
        {
            "agreement": {
                "id": 1,
                "is_current": False,
                "links": {
                    "self": "http://localhost:8000/agreements/1"
                },
                "url": "https://marketplace.service.gov.au/static/media/documents/digital.pdf",
                "version": "Marketplace Agreement 2.0"
            },
            "agreement_id": 1,
            "application_id": 2,
            "links": {},
            "signed_at": "2017-01-20T01:11:04.848011+00:00",
            "supplier_code": 0,
            "user_id": 365
        }
    ],
    "is_recruiter": "false",
    "lastUpdateTime": "2017-09-27T10:11:56.429856+00:00",
    "last_update_time": "2017-09-27T10:11:56.429856+00:00",
    "linkedin": "http://linkedin.com/yo/laland",
    "links": {
        "self": "http://localhost:8000/suppliers/1818"
    },
    "longName": "Example Pty Ltd",
    "long_name": "Example Pty Ltd",
    "name": "Apple Inc Pty Ltd",
    "phone": "0458212000",
    "prices": [],
    "products": [],
    "recruiter_info": {},
    "references": [],
    "representative": "Anne Example Shmample the third",
    "seller_types": {
        "recruitment": "false"
    },
    "services": {},
    "signed_agreements": [
        {
            "agreement": {
                "id": 1,
                "is_current": False,
                "links": {
                    "self": "http://localhost:8000/agreements/1"
                },
                "url": "https://marketplace.service.gov.au/static/media/documents/digital.pdf",
                "version": "Marketplace Agreement 2.0"
            },
            "agreement_id": 1,
            "application_id": 2,
            "links": {},
            "signed_at": "2017-01-20T01:11:04.848011+00:00",
            "supplier_code": 0,
            "user_id": 365
        }
    ],
    "status": "complete",
    "summary": "An example apple company. zs",
    "text_vector": "'appl':1A,7B,12C 'compani':8B,13C 'exampl':6B,11C 'inc':2A 'ltd':4A 'pti':3A 'zs':9B,14C",
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
                        'supplier': {'abn': '1', 'email': None, 'contact': None, 'name': 'Test Supplier1'}}


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
    print start_date, end_date
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
                                     'startDate': str(start_date),
                                     'endDate': str(end_date)}]}),
        content_type='application/json')
    assert response.status_code == 200

    prices = json.loads(response.data)['prices']
    assert prices[0]['startDate'] == pendulum.parse(str(date_from)).format('DD/MM/YYYY')
    assert prices[0]['endDate'] == start_date.subtract(days=1).format('DD/MM/YYYY')
    assert prices[0]['price'] == existing_price
    assert prices[1]['startDate'] == start_date.format('DD/MM/YYYY')
    assert prices[1]['endDate'] == end_date.format('DD/MM/YYYY')
    assert prices[1]['price'] == str(new_price)
    assert prices[2]['startDate'] == end_date.add(days=1).format('DD/MM/YYYY')
    assert prices[2]['endDate'] == pendulum.create(2050, 1, 1).format('DD/MM/YYYY')
    assert prices[2]['price'] == existing_price
