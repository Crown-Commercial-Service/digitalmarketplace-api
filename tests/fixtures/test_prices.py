import json
import pendulum


def test_filter_prices(client, supplier_user, service_type_prices):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.get('/2/prices/suppliers/{}/services/1/categories/1'.format(supplier_user.supplier_code))
    assert response.status_code == 200

    price = json.loads(response.data)['prices'][0]
    assert price['capPrice'] == '321.56'
    assert price['price'] == '200.50'


def test_update_prices(client, supplier_user, service_type_prices):
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
        '/2/prices',
        data=json.dumps({'price': []}),
        content_type='application/json')
    assert response.status_code == 400
    assert json.loads(response.data)['message'] == '\'prices\' is a required property'

    response = client.post(
        '/2/prices',
        data=json.dumps({'prices': [{'id': id, 'price': new_price,
                                     'startDate': 'invalid start',
                                     'endDate': str(end_date)}]}),
        content_type='application/json')
    assert response.status_code == 400
    assert json.loads(response.data)['message'] == 'Invalid date string: invalid start'

    response = client.post(
        '/2/prices',
        data=json.dumps({'prices': [{'id': id, 'price': new_price,
                                     'startDate': str(pendulum.Date.today()),
                                     'endDate': str(end_date)}]}),
        content_type='application/json')
    assert response.status_code == 400
    assert json.loads(response.data)['message'] == 'startDate must be in the future: {}'.format(pendulum.Date.today())

    response = client.post(
        '/2/prices',
        data=json.dumps({'prices': [{'id': id, 'price': new_price,
                                     'startDate': str(start_date),
                                     'endDate': str(pendulum.Date.today())}]}),
        content_type='application/json')
    assert response.status_code == 400
    assert json.loads(response.data)['message'] == 'endDate must be after startDate: {}'.format(pendulum.Date.today())

    response = client.post(
        '/2/prices',
        data=json.dumps({'prices': [{'id': id, 'price': 1000,
                                     'startDate': str(start_date),
                                     'endDate': str(end_date)}]}),
        content_type='application/json')
    assert response.status_code == 400
    assert json.loads(response.data)['message'] == 'price must be less than capPrice: 1000'

    response = client.post(
        '/2/prices',
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
