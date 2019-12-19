import json
import pytest
import mock
from app import encryption
from app.models import db, utcnow, Supplier, SupplierFramework, Contact, SupplierDomain, User,\
    Framework, UserFramework, AuditEvent, BriefResponse
from app.api.services import brief_responses_service
from tests.app.helpers import COMPLETE_SPECIALIST_BRIEF
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
                code=i,
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


@pytest.fixture()
def supplier_users(app, request, suppliers):
    with app.app_context():
        i = 102
        for supplier in suppliers:
            db.session.add(User(
                id=i,
                email_address='j@examplecompany%s.biz' % i,
                name=fake.name(),
                password=encryption.hashpw('testpassword'),
                active=True,
                role='supplier',
                supplier_code=supplier.code,
                password_changed_at=utcnow()
            ))
            db.session.flush()
            framework = Framework.query.filter(Framework.slug == "digital-marketplace").first()
            db.session.add(UserFramework(user_id=i, framework_id=framework.id))
            i += 1

        db.session.commit()
        yield User.query.filter(User.role == 'supplier').all()


@pytest.fixture()
def brief_responses_specialist(app, request, supplier_users):
    params = request.param if hasattr(request, 'param') else {}
    include_resume = params['include_resume'] if 'include_resume' in params else True
    with app.app_context():
        response_id = 1
        for supplier_user in supplier_users:
            for i in range(1, 4):
                data = {
                    'specialistGivenNames': 'a',
                    'specialistSurname': 'b',
                    'previouslyWorked': 'x',
                    'visaStatus': 'y',
                    'essentialRequirements': [
                        {'TEST': 'xxx'},
                        {'TEST 2': 'yyy'}
                    ],
                    'availability': '01/01/2018',
                    'respondToEmailAddress': 'supplier@email.com',
                    'specialistName': 'Test Specialist Name',
                    'dayRate': '100',
                    'dayRateExcludingGST': '91',
                    'attachedDocumentURL': [
                        'test-%s-%s.pdf' % (supplier_user.id, i), 'test-2-%s-%s.pdf' % (supplier_user.id, i)
                    ]
                }
                if include_resume:
                    data['resume'] = ['resume-%s-%s.pdf' % (supplier_user.id, i)]
                db.session.add(BriefResponse(
                    id=response_id,
                    brief_id=1,
                    supplier_code=supplier_user.supplier_code,
                    submitted_at=pendulum.now(),
                    data=data
                ))
                i += 1
                response_id += 1
            db.session.flush()

        db.session.commit()
        yield BriefResponse.query.all()


@pytest.fixture()
def brief_responses_rfx(app, request, supplier_users):
    params = request.param if hasattr(request, 'param') else {}
    include_response_template = params['include_response_template'] if 'include_response_template' in params else True
    with app.app_context():
        response_id = 1
        for supplier_user in supplier_users:
            for i in range(1, 4):
                data = {
                    'respondToEmailAddress': 'supplier@email.com',
                    'attachedDocumentURL': [
                        'test-%s-%s.pdf' % (supplier_user.id, i),
                        'test-2-%s-%s.pdf' % (supplier_user.id, i)
                    ]
                }
                if include_response_template:
                    data['responseTemplate'] = ['response-%s-%s.pdf' % (supplier_user.id, i)]
                db.session.add(BriefResponse(
                    id=response_id,
                    brief_id=1,
                    supplier_code=supplier_user.supplier_code,
                    submitted_at=pendulum.now(),
                    data=data
                ))
                i += 1
                response_id += 1
            db.session.flush()

        db.session.commit()
        yield BriefResponse.query.all()


@pytest.fixture()
def brief_responses_rfx_with_proposal(app, request, supplier_users):
    with app.app_context():
        response_id = 1
        for supplier_user in supplier_users:
            for i in range(1, 4):
                db.session.add(BriefResponse(
                    id=response_id,
                    brief_id=1,
                    supplier_code=supplier_user.supplier_code,
                    submitted_at=pendulum.now(),
                    data={
                        'respondToEmailAddress': 'supplier@email.com',
                        'writtenProposal': ['proposal-%s-%s.pdf' % (supplier_user.id, i)],
                        'attachedDocumentURL': [
                            'test-%s-%s.pdf' % (supplier_user.id, i),
                            'test-2-%s-%s.pdf' % (supplier_user.id, i)
                        ]
                    }
                ))
                i += 1
                response_id += 1
            db.session.flush()

        db.session.commit()
        yield BriefResponse.query.all()


@pytest.fixture()
def brief_responses_atm(app, request, supplier_users):
    params = request.param if hasattr(request, 'param') else {}
    include_written_proposal = params['include_written_proposal'] if 'include_written_proposal' in params else True
    with app.app_context():
        response_id = 1
        for supplier_user in supplier_users:
            for i in range(1, 4):
                data = {
                    'respondToEmailAddress': 'supplier@email.com',
                    'respondToPhone': '0263636363',
                    'attachedDocumentURL': [
                        'test-%s-%s.pdf' % (supplier_user.id, i),
                        'test-2-%s-%s.pdf' % (supplier_user.id, i)
                    ],
                    'criteria': {
                        'TEST': 'bla bla',
                        'TEST 2': 'bla bla'
                    }
                }
                if include_written_proposal:
                    data['writtenProposal'] = ['proposal-%s-%s.pdf' % (supplier_user.id, i)]
                db.session.add(BriefResponse(
                    id=response_id,
                    brief_id=1,
                    supplier_code=supplier_user.supplier_code,
                    submitted_at=pendulum.now(),
                    data=data
                ))
                i += 1
                response_id += 1
            db.session.flush()

        db.session.commit()
        yield BriefResponse.query.all()


@mock.patch('app.tasks.publish_tasks.brief_response')
def test_get_brief_response(brief_response, client, supplier_user, supplier_domains, briefs, assessments, suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    for i in range(1, 3):
        res = client.post('/2/brief/1/respond')
        assert res.status_code == 201
        data = json.loads(res.get_data(as_text=True))

        res = client.patch(
            '/2/brief/1/respond/%s' % data['id'],
            data=json.dumps({
                'submit': True,
                'specialistGivenNames': 'a',
                'specialistSurname': 'b',
                'previouslyWorked': 'x',
                'visaStatus': 'y',
                'essentialRequirements': [
                    {'TEST': 'xxx'},
                    {'TEST 2': 'yyy'}
                ],
                'availability': '01/01/2018',
                'respondToEmailAddress': 'supplier@email.com',
                'specialistName': 'Test Specialist Name',
                'dayRate': '100',
                'dayRateExcludingGST': '91',
                'resume': ['resume.pdf'],
                'attachedDocumentURL': [
                    'test.pdf'
                ]
            }),
            content_type='application/json'
        )
        assert res.status_code == 200
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
        res = client.post('/2/brief/1/respond')
        assert res.status_code == 201
        data = json.loads(res.get_data(as_text=True))

        res = client.patch(
            '/2/brief/1/respond/%s' % data['id'],
            data=json.dumps({
                'submit': True,
                'specialistGivenNames': 'a',
                'specialistSurname': 'b',
                'previouslyWorked': 'x',
                'visaStatus': 'y',
                'essentialRequirements': [
                    {'TEST': 'xxx'},
                    {'TEST 2': 'yyy'}
                ],
                'availability': '01/01/2018',
                'respondToEmailAddress': 'supplier@email.com',
                'specialistName': 'Test Specialist Name',
                'dayRate': '100',
                'dayRateExcludingGST': '91',
                'resume': ['resume.pdf'],
                'attachedDocumentURL': [
                    'test.pdf'
                ]
            }),
            content_type='application/json'
        )
        assert res.status_code == 200
        assert brief_response.delay.called is True

        res = client.get(
            '/2/brief-response/{}'.format(i),
            content_type='application/json'
        )
        assert res.status_code == 200

        res = client.put(
            '/2/brief-response/{}/withdraw'.format(i),
            data=json.dumps({
                'essentialRequirements': [
                    {'TEST': 'xxx'},
                    {'TEST 2': 'yyy'}
                ],
                'availability': '01/01/2018',
                'respondToEmailAddress': 'supplier@email.com',
                'specialistName': 'Test Specialist Name',
                'dayRate': '100',
                'dayRateExcludingGST': '91',
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
        res = client.post('/2/brief/1/respond')
        assert res.status_code == 201
        data = json.loads(res.get_data(as_text=True))

        res = client.patch(
            '/2/brief/1/respond/%s' % data['id'],
            data=json.dumps({
                'submit': True,
                'specialistGivenNames': 'a',
                'specialistSurname': 'b',
                'previouslyWorked': 'x',
                'visaStatus': 'y',
                'essentialRequirements': [
                    {'TEST': 'xxx'},
                    {'TEST 2': 'yyy'}
                ],
                'availability': '01/01/2018',
                'respondToEmailAddress': 'supplier@email.com',
                'specialistName': 'Test Specialist Name',
                'dayRate': '100',
                'dayRateExcludingGST': '91',
                'resume': ['resume.pdf'],
                'attachedDocumentURL': [
                    'test.pdf'
                ]
            }),
            content_type='application/json'
        )
        assert res.status_code == 200
        assert brief_response.delay.called is True

        res = client.put(
            '/2/brief-response/{}/withdraw'.format(i),
            data=json.dumps({
                'essentialRequirements': [
                    {'TEST': 'xxx'},
                    {'TEST 2': 'yyy'}
                ],
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
                'essentialRequirements': [
                    {'TEST': 'xxx'},
                    {'TEST 2': 'yyy'}
                ],
                'availability': '01/01/2018',
                'respondToEmailAddress': 'supplier@email.com',
                'specialistName': 'Test Specialist Name',
                'dayRate': '100',
                'dayRateExcludingGST': '91',
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

    res = client.post('/2/brief/1/respond')
    assert res.status_code == 201
    data = json.loads(res.get_data(as_text=True))

    res = client.patch(
        '/2/brief/1/respond/%s' % data['id'],
        data=json.dumps({
            'submit': True,
            'respondToEmailAddress': 'supplier@email.com',
            'responseTemplate': ['response.pdf'],
            'attachedDocumentURL': [
                'test.pdf'
            ]
        }),
        content_type='application/json'
    )
    assert res.status_code == 200
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

    res = client.post('/2/brief/1/respond')
    assert res.status_code == 403


@pytest.fixture()
def atm_data(app, request):
    params = request.param if hasattr(request, 'param') else {}
    evaluationType = params['evaluationType'] if 'evaluationType' in params else []
    requestMoreInfo = params['requestMoreInfo'] if 'requestMoreInfo' in params else 'no'
    yield {
        'title': 'TEST',
        'organisation': 'ABC',
        'summary': 'TEST',
        'location': [
            'New South Wales'
        ],
        'sellerCategory': '',
        'openTo': 'all',
        'requestMoreInfo': requestMoreInfo,
        'evaluationType': evaluationType,
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

    res = client.post('/2/brief/1/respond')
    assert res.status_code == 201
    data = json.loads(res.get_data(as_text=True))

    res = client.patch(
        '/2/brief/1/respond/%s' % data['id'],
        data=json.dumps({
            'submit': True,
            'respondToEmailAddress': 'supplier@email.com',
            'criteria': {
                'TEST': 'bla bla',
                'TEST 2': 'bla bla'
            }
        }),
        content_type='application/json'
    )
    assert res.status_code == 200
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

    res = client.post('/2/brief/1/respond')
    assert res.status_code == 201
    data = json.loads(res.get_data(as_text=True))

    res = client.patch(
        '/2/brief/1/respond/%s' % data['id'],
        data=json.dumps({
            'submit': True,
            'respondToEmailAddress': 'supplier@email.com',
            'criteria': {
                'TEST': 'bla bla',
                'TEST 2': 'bla bla'
            }
        }),
        content_type='application/json'
    )
    assert res.status_code == 200
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

    res = client.post('/2/brief/1/respond')
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

    res = client.post('/2/brief/1/respond')
    assert res.status_code == 201
    data = json.loads(res.get_data(as_text=True))

    res = client.patch(
        '/2/brief/1/respond/%s' % data['id'],
        data=json.dumps({
            'submit': True,
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

    res = client.post('/2/brief/1/respond')
    assert res.status_code == 201
    data = json.loads(res.get_data(as_text=True))

    res = client.patch(
        '/2/brief/1/respond/%s' % data['id'],
        data=json.dumps({
            'submit': True,
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

    res = client.post('/2/brief/1/respond')
    assert res.status_code == 201
    data = json.loads(res.get_data(as_text=True))

    res = client.patch(
        '/2/brief/1/respond/%s' % data['id'],
        data=json.dumps({
            'submit': True,
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

    res = client.post('/2/brief/1/respond')
    assert res.status_code == 201
    data = json.loads(res.get_data(as_text=True))

    res = client.patch(
        '/2/brief/1/respond/%s' % data['id'],
        data=json.dumps({
            'submit': True,
            'respondToEmailAddress': 'supplier@email.com',
            'respondToPhone': '0263636363',
            'writtenProposal': ['proposal.pdf'],
            'attachedDocumentURL': ['TEST.pdf'],
            'criteria': {
                'TEST': 'bla bla',
                'TEST 2': 'bla bla'
            }
        }),
        content_type='application/json'
    )
    assert res.status_code == 200
    assert brief_response.delay.called is True


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
@pytest.mark.parametrize('brief_responses_specialist', [{'include_resume': False}], indirect=True)
def test_brief_response_edit_previous_submitted_without_doc_specialist(brief_response, brief, client, suppliers,
                                                                       supplier_user, supplier_domains,
                                                                       briefs, brief_responses_specialist,
                                                                       supplier_users):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    brief_response = brief_responses_specialist[0]
    assert brief_response.status == 'submitted'
    assert brief_response.data.get('resume', []) == []

    # success without a resume but with attachedDocumentURL
    res = client.patch(
        '/2/brief/1/respond/%s' % brief_response.id,
        data=json.dumps({
            'submit': True,
            'specialistGivenNames': 'a',
            'specialistSurname': 'b',
            'previouslyWorked': 'x',
            'visaStatus': 'y',
            'essentialRequirements': [
                {'TEST': 'xxx'},
                {'TEST 2': 'yyy'}
            ],
            'availability': '01/01/2018',
            'respondToEmailAddress': 'supplier@email.com',
            'specialistName': 'Test Specialist Name',
            'dayRate': '100',
            'dayRateExcludingGST': '91',
            'attachedDocumentURL': ['test-1.pdf']
        }),
        content_type='application/json'
    )
    assert res.status_code == 200

    # failure without a resume or attachedDocumentURL
    res = client.patch(
        '/2/brief/1/respond/%s' % brief_response.id,
        data=json.dumps({
            'submit': True,
            'specialistGivenNames': 'a',
            'specialistSurname': 'b',
            'previouslyWorked': 'x',
            'visaStatus': 'y',
            'essentialRequirements': [
                {'TEST': 'xxx'},
                {'TEST 2': 'yyy'}
            ],
            'availability': '01/01/2018',
            'respondToEmailAddress': 'supplier@email.com',
            'specialistName': 'Test Specialist Name',
            'dayRate': '100',
            'dayRateExcludingGST': '91',
            'attachedDocumentURL': []
        }),
        content_type='application/json'
    )
    assert res.status_code == 400


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
@pytest.mark.parametrize('brief_responses_rfx', [{'include_response_template': False}], indirect=True)
@pytest.mark.parametrize('briefs', [{'lot_slug': 'rfx', 'unpublished': True}], indirect=True)
def test_brief_response_edit_previous_submitted_without_doc_rfx(brief_response, brief, client, suppliers,
                                                                supplier_user, supplier_domains, buyer_user,
                                                                briefs, rfx_data, brief_responses_rfx,
                                                                supplier_users):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    brief_response = brief_responses_rfx[0]
    assert brief_response.status == 'submitted'
    assert brief_response.data.get('responseTemplate', []) == []

    # success without a response template but with attachedDocumentURL
    res = client.patch(
        '/2/brief/1/respond/%s' % brief_response.id,
        data=json.dumps({
            'submit': True,
            'respondToEmailAddress': 'supplier@email.com',
            'attachedDocumentURL': [
                'test.pdf'
            ]
        }),
        content_type='application/json'
    )
    assert res.status_code == 200

    # failure without a response template or attachedDocumentURL
    res = client.patch(
        '/2/brief/1/respond/%s' % brief_response.id,
        data=json.dumps({
            'submit': True,
            'respondToEmailAddress': 'supplier@email.com',
            'attachedDocumentURL': []
        }),
        content_type='application/json'
    )
    assert res.status_code == 400


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
@pytest.mark.parametrize('brief_responses_atm', [{'include_written_proposal': False}], indirect=True)
@pytest.mark.parametrize('briefs', [{'lot_slug': 'atm', 'unpublished': True}], indirect=True)
@pytest.mark.parametrize('atm_data', [{'evaluationType': ['Case study'], 'requestMoreInfo': 'yes'}], indirect=True)
def test_brief_response_edit_previous_submitted_without_doc_atm(brief_response, brief, client, suppliers,
                                                                supplier_user, supplier_domains, buyer_user,
                                                                briefs, atm_data, brief_responses_atm,
                                                                supplier_users):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    brief_response = brief_responses_atm[0]
    assert brief_response.status == 'submitted'
    assert brief_response.data.get('writtenProposal', []) == []

    # success without a response template but with attachedDocumentURL
    res = client.patch(
        '/2/brief/1/respond/%s' % brief_response.id,
        data=json.dumps({
            'submit': True,
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
    assert res.status_code == 200

    # failure without a response template or attachedDocumentURL
    res = client.patch(
        '/2/brief/1/respond/%s' % brief_response.id,
        data=json.dumps({
            'submit': True,
            'respondToEmailAddress': 'supplier@email.com',
            'respondToPhone': '0263636363',
            'attachedDocumentURL': [],
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
def test_brief_responses_get_attachments_specialist(brief_response, brief, app, client, suppliers, supplier_domains,
                                                    specialist_brief, brief_responses_specialist, supplier_users):
    attachments = brief_responses_service.get_all_attachments(1)
    assert len(attachments) == 45
    i = 1
    for supplier_user in supplier_users:
        user_attachments = [x['file_name'] for x in attachments if x['supplier_code'] == supplier_user.supplier_code]
        for i in range(1, 4):
            assert 'test-%s-%s.pdf' % (supplier_user.id, i) in user_attachments
            assert 'test-2-%s-%s.pdf' % (supplier_user.id, i) in user_attachments
            assert 'resume-%s-%s.pdf' % (supplier_user.id, i) in user_attachments


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
def test_brief_responses_get_attachments_rfx(brief_response, brief, app, client, suppliers, supplier_domains,
                                             rfx_brief, brief_responses_rfx, supplier_users):
    attachments = brief_responses_service.get_all_attachments(1)
    assert len(attachments) == 45
    i = 1
    for supplier_user in supplier_users:
        user_attachments = [x['file_name'] for x in attachments if x['supplier_code'] == supplier_user.supplier_code]
        for i in range(1, 4):
            assert 'test-%s-%s.pdf' % (supplier_user.id, i) in user_attachments
            assert 'test-2-%s-%s.pdf' % (supplier_user.id, i) in user_attachments
            assert 'response-%s-%s.pdf' % (supplier_user.id, i) in user_attachments


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
def test_brief_responses_get_attachments_rfx_with_proposal(brief_response, brief, app, client, suppliers,
                                                           supplier_domains, rfx_brief,
                                                           brief_responses_rfx_with_proposal, supplier_users):
    attachments = brief_responses_service.get_all_attachments(1)
    assert len(attachments) == 45
    i = 1
    for supplier_user in supplier_users:
        user_attachments = [x['file_name'] for x in attachments if x['supplier_code'] == supplier_user.supplier_code]
        for i in range(1, 4):
            assert 'test-%s-%s.pdf' % (supplier_user.id, i) in user_attachments
            assert 'test-2-%s-%s.pdf' % (supplier_user.id, i) in user_attachments
            assert 'proposal-%s-%s.pdf' % (supplier_user.id, i) in user_attachments


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
def test_brief_responses_get_attachments_atm(brief_response, brief, app, client, suppliers, supplier_domains,
                                             atm_brief, brief_responses_atm, supplier_users):
    attachments = brief_responses_service.get_all_attachments(1)
    assert len(attachments) == 45
    i = 1
    for supplier_user in supplier_users:
        user_attachments = [x['file_name'] for x in attachments if x['supplier_code'] == supplier_user.supplier_code]
        for i in range(1, 4):
            assert 'test-%s-%s.pdf' % (supplier_user.id, i) in user_attachments
            assert 'test-2-%s-%s.pdf' % (supplier_user.id, i) in user_attachments
            assert 'proposal-%s-%s.pdf' % (supplier_user.id, i) in user_attachments


@mock.patch('app.tasks.publish_tasks.brief')
@mock.patch('app.tasks.publish_tasks.brief_response')
def test_brief_responses_get_attachments_training2(brief_response, brief, app, client, suppliers, supplier_domains,
                                                   training2_brief, brief_responses_rfx, supplier_users):
    attachments = brief_responses_service.get_all_attachments(1)
    assert len(attachments) == 45
    i = 1
    for supplier_user in supplier_users:
        user_attachments = [x['file_name'] for x in attachments if x['supplier_code'] == supplier_user.supplier_code]
        for i in range(1, 4):
            assert 'test-%s-%s.pdf' % (supplier_user.id, i) in user_attachments
            assert 'test-2-%s-%s.pdf' % (supplier_user.id, i) in user_attachments
            assert 'response-%s-%s.pdf' % (supplier_user.id, i) in user_attachments
