import json


def test_create_assessment(client, suppliers, domains, supplier_domains, briefs):
    supplier_domain = supplier_domains[0]
    supplier = [s for s in suppliers if s.id == supplier_domain.supplier_id][0]
    domain = [d for d in domains if d.id == supplier_domain.domain_id][0]
    brief = briefs[0]

    res = client.post(
        '/assessments',
        data=json.dumps({
            'assessment': {
                'supplier_code': supplier.code,
                'domain_name': domain.name,
                'brief_id': brief.id
            }
        }),
        content_type='application/json'
    )

    assert res.status_code == 201
    data = json.loads(res.get_data(as_text=True))
    assessment = data['assessment']

    assert assessment['briefs'][0]['id'] == brief.id
    assert assessment['supplier_domain']['id'] == supplier_domain.id


def test_create_assessment_with_supplier_domain(client, supplier_domains, briefs):
    supplier_domain = supplier_domains[0]
    brief = briefs[0]

    res = client.post(
        '/assessments',
        data=json.dumps({
            'assessment': {
                'supplier_domain_id': supplier_domain.id,
                'brief_id': brief.id
            }
        }),
        content_type='application/json'
    )

    assert res.status_code == 201
    data = json.loads(res.get_data(as_text=True))
    assessment = data['assessment']

    assert assessment['briefs'][0]['id'] == brief.id
    assert assessment['supplier_domain']['id'] == supplier_domain.id


def test_list_assessment(client, assessments):
    res = client.get('/assessments')

    assert res.status_code == 200
    data = json.loads(res.get_data(as_text=True))

    assert len(data['assessments']) == len(assessments)
