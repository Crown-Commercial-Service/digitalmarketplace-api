import json
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
    "frameworks": [],
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
    "signed_agreements": [],
    "status": "complete",
    "summary": "An example apple company. zs",
    "text_vector": "'appl':1A,7B,12C 'compani':8B,13C 'exampl':6B,11C 'inc':2A 'ltd':4A 'pti':3A 'zs':9B,14C",
    "website": "https://example.com/yo/yo/d"
}


def test_require_supplier_role_for_profile(app, supplier_user, client, mocker):
    response = client.post(
        '/supplier',
        data=json.dumps(form_data),
        content_type='application/json')

    assert response.status_code == 401


def test_update_supplier_profile(app, supplier_user, client, mocker):
    res = client.post('/login', data=json.dumps({
        'emailAddress': supplier_user.email_address, 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    assert not hasattr(supplier_user, 'addresses')
    assert not hasattr(supplier_user, 'contacts')

    form_data['code'] = supplier_user.supplier_code
    form_data['id'] = supplier_user.id

    response = client.post(
        '/supplier',
        data=json.dumps(form_data),
        content_type='application/json')

    assert response.status_code == 200

    supplier_data = json.loads(response.data)

    assert supplier_data['user']['addresses'] is not None
    assert type(supplier_data['user']['addresses']) == list

    assert supplier_data['user']['contacts'] is not None
    assert type(supplier_data['user']['contacts']) == list

    updated_supplier_instance = Supplier.query.filter(
        Supplier.code == supplier_data['user'].get('code')).first()

    assert hasattr(updated_supplier_instance, 'addresses')
    assert hasattr(updated_supplier_instance, 'contacts')
