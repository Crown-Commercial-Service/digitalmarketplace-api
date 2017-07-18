import json
from nose.tools import assert_equal


def test_duplicate_supplier_with_same_domain(client, supplier_user):
    response = client.post(
        '/signup',
        data=json.dumps({
            'email_address': 'm@examplecompany.biz',
            'name': 'Jeff Labowski'
        }),
        content_type='application/json')
    assert response.status_code == 409
    data = response.get_data(as_text=True)

    assert_equal(data, 'An account with this email domain already exists')


def test_duplicate_application_with_same_domain(client, application_user):
    response = client.post(
        '/signup',
        data=json.dumps({
            'email_address': 'm@don.com',
            'name': 'Jeff Labowski'
        }),
        content_type='application/json')
    assert response.status_code == 409

    data = response.get_data(as_text=True)
    assert data == 'An account with this email domain already exists'


def test_unqiue_domain(client):
    response = client.post(
        '/signup',
        data=json.dumps({
            'email_address': 'm@something.com',
            'name': 'Jeff Labowski'
        }),
        content_type='application/json')
    assert response.status_code == 200

    data = response.get_data(as_text=True)
    assert data == 'Email invite sent successfully'


def test_generic_domain(client):
    response = client.post(
        '/signup',
        data=json.dumps({
            'email_address': 'm@gmail.com',
            'name': 'Jeff Labowski'
        }),
        content_type='application/json')
    assert response._status_code == 200

    data = response.get_data(as_text=True)
    assert data == 'Email invite sent successfully'
