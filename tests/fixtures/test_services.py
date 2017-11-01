import json

REGIONS = [
    {
        'name': 'NSW',
        'subRegions': [{'id': 1, 'name': 'Metro'}, {'id': 2, 'name': 'Remote'}]},
    {
        'name': 'QLD',
        'subRegions': [{'id': 3, 'name': 'Metro'}]}]

SERVICES = [
    {
        'name': 'Medical',
        'subCategories': [{'id': 1, 'name': 'Service1'}]},
    {
        'name': 'Rehabilitation',
        'subCategories': [{'id': 2, 'name': 'Service2'}]}]


def test_get_regions(client, users, regions):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.get('/2/regions')

    assert response.status_code == 200

    regions = json.loads(response.data)
    assert regions['regions'] == REGIONS


def test_get_services(client, users, services):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.get('/2/services')

    assert response.status_code == 200

    services = json.loads(response.data)
    assert services['categories'] == SERVICES


def test_search_catalogue(client, users, service_type_prices):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'test@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.get('/2/services/10/regions/12/prices')

    assert response.status_code == 200

    empty_prices = json.loads(response.data)
    category = len(empty_prices['categories']) == 0

    response = client.get('/2/services/1/regions/1/prices')

    assert response.status_code == 200

    no_sub_type = json.loads(response.data)
    category = no_sub_type['categories'][0]
    assert category['name'] == ''
    assert category['suppliers'][0]['price'] == '200.50'

    response = client.get('/2/services/2/regions/2/prices')

    assert response.status_code == 200

    prices = json.loads(response.data)
    category = prices['categories'][0]
    assert category['name'] == 'SubType1'
    assert category['suppliers'][0]['price'] == '200.90'
