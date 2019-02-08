import json
import mock


@mock.patch('app.jiraapi.JIRA')
@mock.patch('app.main.views.assessments.get_marketplace_jira')
@mock.patch('app.tasks.publish_tasks.assessment')
def test_create_assessment(assessment_task,
                           get_marketplace_jira,
                           jira,
                           bearer,
                           client,
                           suppliers,
                           domains,
                           supplier_domains,
                           briefs):
    supplier_domain = supplier_domains[0]
    supplier = [s for s in suppliers if s.id == supplier_domain.supplier_id][0]
    domain = [d for d in domains if d.id == supplier_domain.domain_id][0]
    brief = briefs[0]

    res = client.post(
        '/assessments',
        data=json.dumps({
            'update_details': {'updated_by': 'test@example.com'},
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
    assert assessment_task.delay.called is True


def test_create_assessment_with_invalid_supplier_domain(bearer, client, suppliers, domains, supplier_domains, briefs):
    domain = domains[-1]
    supplier = suppliers[0]
    brief = briefs[0]

    res = client.post(
        '/assessments',
        data=json.dumps({
            'update_details': {'updated_by': 'test@example.com'},
            'assessment': {
                'supplier_code': supplier.code,
                'domain_name': domain.name,
                'brief_id': brief.id
            }
        }),
        content_type='application/json'
    )
    assert res.status_code == 400


@mock.patch('app.tasks.publish_tasks.assessment')
def test_create_assessment_with_existing_assessment(assessment_task, bearer, client, assessments):
    assessment = assessments[0]
    domain = assessment.supplier_domain.domain
    supplier = assessment.supplier_domain.supplier
    brief = assessment.briefs[0]

    res = client.post(
        '/assessments',
        data=json.dumps({
            'update_details': {'updated_by': 'test@example.com'},
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
    result = data['assessment']
    assert assessment_task.delay.called is True

    assert result['briefs'][0]['id'] == brief.id
    assert result['supplier_domain']['id'] == assessment.supplier_domain.id


def test_list_assessment(bearer, client, assessments):
    res = client.get('/assessments')

    assert res.status_code == 200
    data = json.loads(res.get_data(as_text=True))

    assert len(data['assessments']) == len(assessments)
