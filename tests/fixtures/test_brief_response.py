import json
import pytest
import mock
from app import encryption
from app.models import db, utcnow, Supplier, SupplierFramework, Contact, SupplierDomain, User,\
    Framework, UserFramework, AuditEvent
from faker import Faker
from dmapiclient.audit import AuditTypes
import pendulum
import copy
fake = Faker()


@pytest.fixture()
def suppliers(app, request):
    with app.app_context():
        for i in range(1, 6):
            db.session.add(Supplier(
                abn=i,
                code=(i),
                name='Test Supplier{}'.format(i),
                contacts=[Contact(name='auth rep', email='auth@rep.com')],
                data={
                    'representative': 'auth rep',
                    'phone': '0123456789',
                    'email': 'auth@rep.com',
                    'documents': {
                        "liability": {
                            "filename": "1.pdf",
                            "expiry": pendulum.tomorrow().date().to_date_string()
                        },
                        "workers": {
                            "filename": "2.pdf",
                            "expiry": pendulum.tomorrow().date().to_date_string()
                        },
                        "financial": {
                            "filename": "3.pdf"
                        }
                    },
                    'pricing': {
                        "Emerging technologies": {
                            "maxPrice": "1000"
                        },
                        "Support and Operations": {
                            "maxPrice": "100"
                        },
                        "Agile delivery and Governance": {
                            "maxPrice": "1000"
                        },
                        "Data science": {
                            "maxPrice": "100"
                        },
                        "Change, Training and Transformation": {
                            "maxPrice": "1000"
                        },
                        "Training, Learning and Development": {
                            "maxPrice": "1000"
                        },
                        "Strategy and Policy": {
                            "maxPrice": "1000"
                        },
                        "Software engineering and Development": {
                            "maxPrice": "1000"
                        },
                        "User research and Design": {
                            "maxPrice": "1000"
                        },
                        "Recruitment": {
                            "maxPrice": "1000"
                        }
                    }
                }
            ))

            db.session.flush()

        framework = Framework.query.filter(Framework.slug == "digital-marketplace").first()
        db.session.add(SupplierFramework(supplier_code=1, framework_id=framework.id))

        db.session.commit()
        yield Supplier.query.all()


@pytest.fixture()
def supplier_domains(app, request, suppliers):
    with app.app_context():
        for s in suppliers:
            for i in range(1, 6):
                db.session.add(SupplierDomain(
                    supplier_id=s.id,
                    domain_id=i,
                    status='assessed'
                ))

                db.session.flush()

        db.session.commit()
        yield SupplierDomain.query.all()


@pytest.fixture()
def supplier_user(app, request, suppliers):
    with app.app_context():
        db.session.add(User(
            id=100,
            email_address='j@examplecompany.biz',
            name=fake.name(),
            password=encryption.hashpw('testpassword'),
            active=True,
            role='supplier',
            supplier_code=suppliers[0].code,
            password_changed_at=utcnow()
        ))
        db.session.commit()
        db.session.flush()
        framework = Framework.query.filter(Framework.slug == "digital-outcomes-and-specialists").first()
        db.session.add(UserFramework(user_id=100, framework_id=framework.id))
        db.session.commit()
        yield User.query.first()


@mock.patch('app.tasks.publish_tasks.brief_response')
def test_get_brief_response(brief_response, client, supplier_user, supplier_domains, briefs, assessments, suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    for i in range(1, 3):
        res = client.post(
            '/2/brief/1/respond',
            data=json.dumps({
                'essentialRequirements': ['ABC', 'XYZ'],
                'availability': '01/01/2018',
                'respondToEmailAddress': 'supplier@email.com',
                'specialistName': 'Test Specialist Name',
                'dayRate': '100',
                'attachedDocumentURL': [
                    'test.pdf'
                ]
            }),
            content_type='application/json'
        )
        assert res.status_code == 201
        assert brief_response.delay.called is True

        res = client.get(
            '/2/brief-response/{}'.format(i),
            content_type='application/json'
        )
        data = json.loads(res.get_data(as_text=True))
        assert res.status_code == 200
        assert data['id'] == i


@mock.patch('app.tasks.publish_tasks.brief_response')
def test_withdraw_brief_response(brief_response,
                                 client,
                                 supplier_user,
                                 supplier_domains,
                                 briefs,
                                 assessments,
                                 suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    # this should continue working because the response has been withdrawn
    for i in range(1, 10):
        res = client.post(
            '/2/brief/1/respond',
            data=json.dumps({
                'essentialRequirements': ['ABC', 'XYZ'],
                'availability': '01/01/2018',
                'respondToEmailAddress': 'supplier@email.com',
                'specialistName': 'Test Specialist Name',
                'dayRate': '100',
                'attachedDocumentURL': [
                    'test.pdf'
                ]
            }),
            content_type='application/json'
        )
        assert res.status_code == 201
        assert brief_response.delay.called is True

        res = client.get(
            '/2/brief-response/{}'.format(i),
            content_type='application/json'
        )
        assert res.status_code == 200

        res = client.put(
            '/2/brief-response/{}/withdraw'.format(i),
            data=json.dumps({
                'essentialRequirements': ['ABC', 'XYZ'],
                'availability': '01/01/2018',
                'respondToEmailAddress': 'supplier@email.com',
                'specialistName': 'Test Specialist Name',
                'dayRate': '100',
            }),
            content_type='application/json'
        )
        assert res.status_code == 200

        res = client.get(
            '/2/brief-response/{}'.format(i),
            content_type='application/json'
        )
        assert res.status_code == 400


@mock.patch('app.tasks.publish_tasks.brief_response')
def test_withdraw_already_withdrawn_brief_response(brief_response,
                                                   client,
                                                   supplier_user,
                                                   supplier_domains,
                                                   briefs,
                                                   assessments,
                                                   suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    for i in range(1, 3):
        res = client.post(
            '/2/brief/1/respond',
            data=json.dumps({
                'essentialRequirements': ['ABC', 'XYZ'],
                'availability': '01/01/2018',
                'respondToEmailAddress': 'supplier@email.com',
                'specialistName': 'Test Specialist Name',
                'dayRate': '100',
                'attachedDocumentURL': [
                    'test.pdf'
                ]
            }),
            content_type='application/json'
        )
        assert res.status_code == 201
        assert brief_response.delay.called is True

        res = client.put(
            '/2/brief-response/{}/withdraw'.format(i),
            data=json.dumps({
                'essentialRequirements': ['ABC', 'XYZ'],
                'availability': '01/01/2018',
                'respondToEmailAddress': 'supplier@email.com',
                'specialistName': 'Test Specialist Name',
                'dayRate': '100'
            }),
            content_type='application/json'
        )
        assert res.status_code == 200

        res = client.put(
            '/2/brief-response/{}/withdraw'.format(i),
            data=json.dumps({
                'essentialRequirements': ['ABC', 'XYZ'],
                'availability': '01/01/2018',
                'respondToEmailAddress': 'supplier@email.com',
                'specialistName': 'Test Specialist Name',
                'dayRate': '100',
            }),
            content_type='application/json'
        )
        assert res.status_code == 400

        res = client.get(
            '/2/brief-response/{}'.format(i),
            content_type='application/json'
        )
        assert res.status_code == 400


@pytest.fixture()
def rfx_data():
    yield {
        'title': 'TEST',
        'organisation': 'ABC',
        'summary': 'TEST',
        'workingArrangements': 'TEST',
        'location': [
            'New South Wales'
        ],
        'sellerCategory': '1',
        'sellers': {
            '1': {
                'name': 'Test Supplier1'
            }
        },
        'evaluationType': [
            'Response template',
            'Written proposal'
        ],
        'proposalType': [
            'Breakdown of costs'
        ],
        'requirementsDocument': [
            'TEST.pdf'
        ],
        'responseTemplate': [
            'TEST2.pdf'
        ],
        'startDate': 'ASAP',
        'contractLength': 'TEST',
        'includeWeightings': True,
        'essentialRequirements': [
            {
                'criteria': 'TEST',
                'weighting': '55'
            },
            {
                'criteria': 'TEST 2',
                'weighting': '45'
            }
        ],
        'niceToHaveRequirements': [],
        'contactNumber': '0263635544'
    }


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
def test_rfx_invited_seller_can_respond(brief_response,
                                        brief,
                                        client,
                                        suppliers,
                                        supplier_user,
                                        supplier_domains,
                                        buyer_user,
                                        rfx_brief,
                                        rfx_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    assert brief.delay.called is True

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post(
        '/2/brief/1/respond',
        data=json.dumps({
            'respondToEmailAddress': 'supplier@email.com',
            'attachedDocumentURL': [
                'test.pdf'
            ]
        }),
        content_type='application/json'
    )
    assert res.status_code == 201
    assert brief_response.delay.called is True


@mock.patch('app.tasks.publish_tasks.brief')
def test_rfx_non_invited_seller_can_not_respond(brief, client, suppliers, supplier_user, supplier_domains, buyer_user,
                                                rfx_brief, rfx_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')
    data['sellers'] = {
        '2': 'Test Supplier1'
    }

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    assert brief.delay.called is True

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post(
        '/2/brief/1/respond',
        data=json.dumps({
            'respondToEmailAddress': 'supplier@email.com',
            'respondToPhone': '0263636363',
            'attachedDocumentURL': [
                'test.pdf'
            ]
        }),
        content_type='application/json'
    )
    assert res.status_code == 403


@pytest.fixture()
def atm_data():
    yield {
        'title': 'TEST',
        'organisation': 'ABC',
        'summary': 'TEST',
        'location': [
            'New South Wales'
        ],
        'sellerCategory': '',
        'openTo': 'all',
        'requestMoreInfo': 'no',
        'evaluationType': [],
        'attachments': [
            'TEST3.pdf'
        ],
        'industryBriefing': 'TEST',
        'startDate': 'ASAP',
        'includeWeightings': True,
        'evaluationCriteria': [
            {
                'criteria': 'TEST',
                'weighting': '55'
            },
            {
                'criteria': 'TEST 2',
                'weighting': '45'
            }
        ],
        'contactNumber': '0263635544',
        'timeframeConstraints': 'TEST',
        'backgroundInformation': 'TEST',
        'outcome': 'TEST',
        'endUsers': 'TEST',
        'workAlreadyDone': 'TEST'
    }


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
def test_atm_invited_seller_can_respond_open_to_all(brief_response, brief, client, suppliers, supplier_user,
                                                    supplier_domains, buyer_user, atm_brief, atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['openTo'] = 'all'
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    assert brief.delay.called is True

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post(
        '/2/brief/1/respond',
        data=json.dumps({
            'respondToEmailAddress': 'supplier@email.com',
            'criteria': {
                'TEST': 'bla bla',
                'TEST 2': 'bla bla'
            }
        }),
        content_type='application/json'
    )
    assert res.status_code == 201
    assert brief_response.delay.called is True


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
def test_atm_seller_can_respond_open_to_category(brief_response, brief, client, suppliers, supplier_user,
                                                 supplier_domains, buyer_user, atm_brief, atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['openTo'] = 'category'
    data['sellerCategory'] = '1'
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    assert brief.delay.called is True

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post(
        '/2/brief/1/respond',
        data=json.dumps({
            'respondToEmailAddress': 'supplier@email.com',
            'criteria': {
                'TEST': 'bla bla',
                'TEST 2': 'bla bla'
            }
        }),
        content_type='application/json'
    )
    assert res.status_code == 201
    assert brief_response.delay.called is True


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
def test_atm_seller_can_not_respond_open_to_category(brief_response, brief, client, suppliers, supplier_user,
                                                     supplier_domains, buyer_user, atm_brief, atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['openTo'] = 'category'
    data['sellerCategory'] = '11'
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    assert brief.delay.called is True

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post(
        '/2/brief/1/respond',
        data=json.dumps({
            'respondToEmailAddress': 'supplier@email.com',
            'respondToPhone': '0263636363',
            'criteria': {
                'TEST': 'bla bla',
                'TEST 2': 'bla bla'
            }
        }),
        content_type='application/json'
    )
    assert res.status_code == 403


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
def test_atm_seller_failed_missing_criteria(brief_response, brief, client, suppliers, supplier_user, supplier_domains,
                                            buyer_user, atm_brief, atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    assert brief.delay.called is True

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post(
        '/2/brief/1/respond',
        data=json.dumps({
            'respondToEmailAddress': 'supplier@email.com',
            'respondToPhone': '0263636363',
            'criteria': {
                'TEST': 'bla bla'
            }
        }),
        content_type='application/json'
    )
    assert res.status_code == 400


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
def test_atm_seller_failed_empty_criteria(brief_response, brief, client, suppliers, supplier_user, supplier_domains,
                                          buyer_user, atm_brief, atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    assert brief.delay.called is True

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post(
        '/2/brief/1/respond',
        data=json.dumps({
            'respondToEmailAddress': 'supplier@email.com',
            'respondToPhone': '0263636363',
            'criteria': {
                'TEST': 'bla bla',
                'TEST 2': ''
            }
        }),
        content_type='application/json'
    )
    assert res.status_code == 400


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
def test_atm_seller_failed_missing_file(brief_response, brief, client, suppliers, supplier_user, supplier_domains,
                                        buyer_user, atm_brief, atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['requestMoreInfo'] = 'yes'
    data['requestMoreInfo'] = 'yes'
    data['evaluationType'].append('Case study')
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    assert brief.delay.called is True

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post(
        '/2/brief/1/respond',
        data=json.dumps({
            'respondToEmailAddress': 'supplier@email.com',
            'respondToPhone': '0263636363',
            'criteria': {
                'TEST': 'bla bla',
                'TEST 2': 'bla bla'
            }
        }),
        content_type='application/json'
    )
    assert res.status_code == 400


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
def test_atm_seller_success_with_file(brief_response, brief, client, suppliers, supplier_user, supplier_domains,
                                      buyer_user, atm_brief, atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['requestMoreInfo'] = 'yes'
    data['evaluationType'].append('Case study')
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    assert brief.delay.called is True

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post(
        '/2/brief/1/respond',
        data=json.dumps({
            'respondToEmailAddress': 'supplier@email.com',
            'respondToPhone': '0263636363',
            'attachedDocumentURL': ['TEST.pdf'],
            'criteria': {
                'TEST': 'bla bla',
                'TEST 2': 'bla bla'
            }
        }),
        content_type='application/json'
    )
    assert res.status_code == 201
    assert brief_response.delay.called is True
