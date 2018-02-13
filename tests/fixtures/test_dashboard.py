import json


def test_seller_dashboard(client, brief_responses, supplier_user):
    code = supplier_user.supplier_code
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.get('/2/seller-dashboard'.format(code))
    assert response.status_code == 200
    item = json.loads(response.data)['items'][0]
    assert item['status'] == 'Response submitted'
    assert item['name'] == 'I need a Developer'
