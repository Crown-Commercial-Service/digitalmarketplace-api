# -*- coding: utf-8 -*-
import json
import pytest

from app import encryption
from app.models import Brief, Lot, db, utcnow, Supplier, SupplierFramework, Contact, SupplierDomain, User,\
    Framework, UserFramework, AuditEvent, FrameworkLot
from app.api.business.validators import RFXDataValidator
from faker import Faker
from dmapiclient.audit import AuditTypes
from workdays import workday
import pendulum

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


def test_create_new_brief_response(client, supplier_user, supplier_domains, briefs, assessments, suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

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


def test_create_brief_response_creates_an_audit_event(client, supplier_user, supplier_domains,
                                                      briefs, assessments, suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

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

    audit_events = AuditEvent.query.filter(
        AuditEvent.type == AuditTypes.create_brief_response.value
    ).all()

    assert len(audit_events) == 1
    assert audit_events[0].data['briefResponseId'] == 1


def test_create_brief_response_with_object(client, supplier_user,
                                           supplier_domains, briefs,
                                           assessments, suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post(
        '/2/brief/1/respond',
        data=json.dumps({
            'essentialRequirements': {'0': 'ABC', '1': 'XYZ'},
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


def test_cannot_respond_to_a_brief_more_than_three_times_from_the_same_supplier(client, supplier_user,
                                                                                supplier_domains, briefs,
                                                                                assessments, suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    for i in range(0, 3):
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
    assert res.status_code == 400
    assert 'There are already 3 brief responses for supplier' in res.get_data(as_text=True)


def test_cannot_respond_to_a_brief_with_wrong_number_of_essential_reqs(client, supplier_user,
                                                                       supplier_domains, briefs,
                                                                       assessments, suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post(
        '/2/brief/1/respond',
        data=json.dumps({
            'essentialRequirements': ['XYZ'],
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
    assert res.status_code == 400
    assert 'Essential requirements must be completed' in res.get_data(as_text=True)


def test_create_brief_response_success_with_audit_exception(client, supplier_user, supplier_domains,
                                                            briefs, assessments, suppliers, mocker):
    audit_event = mocker.patch('app.api.views.briefs.audit_service')
    audit_event.side_effect = Exception('Test')

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

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


def test_create_brief_response_fail_with_incorrect_attachment(client, supplier_user, supplier_domains,
                                                              briefs, assessments, suppliers, mocker):
    audit_event = mocker.patch('app.api.views.briefs.audit_service')
    audit_event.side_effect = Exception('Test')

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post(
        '/2/brief/1/respond',
        data=json.dumps({
            'essentialRequirements': ['ABC', 'XYZ'],
            'availability': '01/01/2018',
            'respondToEmailAddress': 'supplier@email.com',
            'specialistName': 'Test Specialist Name',
            'dayRate': '100',
            'attachedDocumentURL': [[{}]]
        }),
        content_type='application/json'
    )
    assert res.status_code == 400

    res = client.post(
        '/2/brief/1/respond',
        data=json.dumps({
            'essentialRequirements': ['ABC', 'XYZ'],
            'availability': '01/01/2018',
            'respondToEmailAddress': 'supplier@email.com',
            'specialistName': 'Test Specialist Name',
            'dayRate': '100',
            'attachedDocumentURL': ['test.exe']
        }),
        content_type='application/json'
    )
    assert res.status_code == 400


def test_get_brief(client, supplier_user, supplier_domains, briefs, assessments, suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

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

    res = client.get(
        '/2/brief/1',
        content_type='application/json'
    )
    data = json.loads(res.get_data(as_text=True))
    assert res.status_code == 200
    assert data['brief']['id'] == 1


@pytest.fixture()
def overview_users(client, app):
    with app.app_context():
        db.session.add(User(
            id=1,
            email_address='me@digital.gov.au',
            name=fake.name(),
            password=encryption.hashpw('test'),
            active=True,
            role='buyer',
            password_changed_at=utcnow()
        ))

        db.session.add(User(
            id=2,
            email_address='dm@digital.gov.au',
            name=fake.name(),
            password=encryption.hashpw('test'),
            active=True,
            role='buyer',
            password_changed_at=utcnow()
        ))

        db.session.commit()

        yield User.query.all()


@pytest.fixture()
def overview_briefs(client, app, overview_users):
    with app.app_context():
        db.session.add(Brief(
            id=1,
            data={'title': 'Python Developer'},
            framework=Framework.query.filter(Framework.slug == "digital-marketplace").first(),
            lot=Lot.query.filter(Lot.slug == 'digital-professionals').first(),
            users=[overview_users[0]]
        ))

        live_brief = Brief(
            id=2,
            data={'title': 'Python Developer'},
            framework=Framework.query.filter(Framework.slug == "digital-marketplace").first(),
            lot=Lot.query.filter(Lot.slug == 'digital-professionals').first(),
            users=[overview_users[0]]
        )

        db.session.add(Brief(
            id=3,
            data={'title': 'WoG HR'},
            framework=Framework.query.filter(Framework.slug == "digital-marketplace").first(),
            lot=Lot.query.filter(Lot.slug == 'digital-outcome').first(),
            users=[overview_users[0]]
        ))

        live_brief.published_at = utcnow()
        live_brief.questions_closed_at = utcnow().add(days=1)
        live_brief.closed_at = utcnow().add(days=2)

        db.session.add(live_brief)
        db.session.commit()

        yield Brief.query.all()


def test_brief_overview_route_responds_successfully(client, overview_briefs):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.get('/2/brief/1/overview', content_type='application/json')
    assert res.status_code == 200


def test_brief_overview_responds_with_brief_title(client, overview_briefs):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    res = client.get('/2/brief/1/overview', content_type='application/json')
    response = json.loads(res.data)

    assert response['title'] == 'Python Developer'


def test_brief_overview_responds_with_sections(client, overview_briefs):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    res = client.get('/2/brief/1/overview', content_type='application/json')
    response = json.loads(res.data)

    assert response['sections']


def test_brief_overview_responds_with_status(client, overview_briefs):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    res = client.get('/2/brief/1/overview', content_type='application/json')
    response = json.loads(res.data)

    assert response['status']


def test_brief_overview_responds_with_403_for_unauthorised_user(client, overview_briefs):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'dm@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    res = client.get('/2/brief/1/overview', content_type='application/json')
    assert res.status_code == 403


def test_brief_overview_responds_with_400_when_lot_is_not_digital_professionals(client, overview_briefs):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    res = client.get('/2/brief/3/overview', content_type='application/json')
    assert res.status_code == 400


def test_brief_overview_responds_with_404_for_missing_brief(client, overview_briefs):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    res = client.get('/2/brief/10/overview', content_type='application/json')
    assert res.status_code == 404


def test_delete_brief_route_responds_successfully(client, overview_briefs):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.delete('/2/brief/1', content_type='application/json')
    assert res.status_code == 200


def test_draft_brief_is_deleted(client, overview_briefs):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    client.delete('/2/brief/1', content_type='application/json')
    briefs = Brief.query.all()

    for brief in briefs:
        assert brief.id != 1


def test_audit_event_is_created_when_brief_is_deleted(client, overview_briefs):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    client.delete('/2/brief/1', content_type='application/json')
    audit_event = AuditEvent.query.first()

    assert audit_event.type == 'delete_brief'
    assert audit_event.user == 'me@digital.gov.au'
    assert 'briefId' in audit_event.data
    assert audit_event.data['briefId'] == 1


def test_live_brief_can_not_be_deleted(client, overview_briefs):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    res = client.delete('/2/brief/2', content_type='application/json')

    assert res.status_code == 400


def test_unauthorised_user_can_not_delete_brief(client, overview_briefs):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'dm@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    res = client.delete('/2/brief/1', content_type='application/json')

    assert res.status_code == 403


def test_404_is_returned_when_deleting_a_missing_brief(client, overview_briefs):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    res = client.delete('/2/brief/10', content_type='application/json')

    assert res.status_code == 404


def test_rfx_brief_create_success_and_visible_to_author(client, buyer_user):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/brief/rfx', content_type='application/json')
    assert res.status_code == 200

    response = json.loads(res.data)
    assert response['id'] == 1

    res = client.get('/2/brief/1', content_type='application/json')
    assert res.status_code == 200


rfx_data = {
    'title': 'TEST',
    'organisation': 'ABC',
    'summary': 'TEST',
    'workingArrangements': 'TEST',
    'location': [
        'New South Wales'
    ],
    'sellerCategory': '1',
    'sellers': {
        '1': 'Seller1'
    },
    'evaluationType': [
        'Response template',
        'Written proposal'
    ],
    'proposalType': [
        'Breakdown of costs',
        'Résumés'
    ],
    'requirementsDocument': [
        'TEST.pdf'
    ],
    'responseTemplate': [
        'TEST2.pdf'
    ],
    'attachments': [
        'TEST3.pdf'
    ],
    'industryBriefing': 'TEST',
    'startDate': 'ASAP',
    'contractLength': 'TEST',
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
    'contactNumber': '0263635544'
}


def test_rfx_field_access_as_owner(client, supplier_domains, suppliers, buyer_user, rfx_brief):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    response = json.loads(res.data)

    res = client.get('/2/brief/1')
    response = json.loads(res.data)
    assert response['brief']['industryBriefing'] == 'TEST'
    assert response['brief']['attachments'] == ['TEST3.pdf']
    assert response['brief']['sellers'] == {'1': 'Seller1'}
    assert response['brief']['evaluationType'] == ['Response template', 'Written proposal']
    assert response['brief']['proposalType'] == ['Breakdown of costs', u'R\xe9sum\xe9s']
    assert response['brief']['requirementsDocument'] == ['TEST.pdf']
    assert response['brief']['responseTemplate'] == ['TEST2.pdf']
    assert response['brief']['contactNumber'] == '0263635544'


def test_rfx_field_access_as_invited_seller(client, supplier_domains, suppliers, buyer_user, rfx_brief, supplier_user):
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

    res = client.get('/2/brief/1')
    response = json.loads(res.data)
    assert response['brief']['industryBriefing'] == 'TEST'
    assert response['brief']['attachments'] == ['TEST3.pdf']
    assert response['brief']['sellers'] == {}
    assert response['brief']['evaluationType'] == ['Response template', 'Written proposal']
    assert response['brief']['proposalType'] == ['Breakdown of costs', u'R\xe9sum\xe9s']
    assert response['brief']['requirementsDocument'] == ['TEST.pdf']
    assert response['brief']['responseTemplate'] == ['TEST2.pdf']
    assert response['brief']['contactNumber'] == ''


def test_rfx_field_access_as_non_invited_seller(client, supplier_domains, suppliers, buyer_user, rfx_brief,
                                                supplier_user):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')
    data['sellers'] = {'2': 'Test Supplier2'}
    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))

    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.get('/2/brief/1')
    response = json.loads(res.data)
    assert response['brief']['industryBriefing'] == ''
    assert response['brief']['attachments'] == []
    assert response['brief']['sellers'] == {}
    assert response['brief']['evaluationType'] == []
    assert response['brief']['proposalType'] == []
    assert response['brief']['requirementsDocument'] == []
    assert response['brief']['responseTemplate'] == []
    assert response['brief']['contactNumber'] == ''


def test_rfx_field_access_as_anonymous_user(client, supplier_domains, suppliers, buyer_user, rfx_brief):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')
    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))

    res = client.get('/2/logout')
    res = client.get('/2/brief/1')
    response = json.loads(res.data)
    assert response['brief']['industryBriefing'] == ''
    assert response['brief']['evaluationType'] == []
    assert response['brief']['responseTemplate'] == []
    assert response['brief']['requirementsDocument'] == []
    assert response['brief']['industryBriefing'] == ''
    assert response['brief']['attachments'] == []
    assert response['brief']['sellers'] == {}
    assert response['brief']['contactNumber'] == ''


def test_rfx_publish_success_2_days_correct_dates(client, supplier_domains, suppliers, buyer_user, rfx_brief):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    response = json.loads(res.data)
    assert response['closedAt'] == pendulum.today().add(days=2).format('%Y-%m-%d')
    question_closing_date = pendulum.instance(workday(pendulum.today(), 1)).format('%Y-%m-%d')
    if question_closing_date > response['closedAt']:
        question_closing_date = pendulum.today().format('%Y-%m-%d')
    assert response['dates']['questions_closing_date'] == question_closing_date


def test_rfx_publish_failure_next_day(client, buyer_user, supplier_domains, suppliers, rfx_brief):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today().add(days=1).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 400


@pytest.fixture()
def get_day_count(request):
    params = request.param if hasattr(request, 'param') else {}
    day_count = params['day_count'] if 'day_count' in params else 0
    return day_count


@pytest.mark.parametrize(
    'get_day_count',
    [{'day_count': 3}, {'day_count': 4}, {'day_count': 5}, {'day_count': 6}, {'day_count': 7}], indirect=True
)
def test_rfx_publish_success_under_one_week_correct_dates(client, buyer_user, supplier_domains, suppliers, rfx_brief,
                                                          get_day_count):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today().add(days=get_day_count).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(rfx_data))
    assert res.status_code == 200
    response = json.loads(res.data)
    assert response['closedAt'] == pendulum.today().add(days=get_day_count).format('%Y-%m-%d')
    question_closing_date = pendulum.instance(workday(pendulum.today(), 2)).format('%Y-%m-%d')
    if question_closing_date > response['closedAt']:
        question_closing_date = response['closedAt']
    assert response['dates']['questions_closing_date'] == question_closing_date


@pytest.mark.parametrize(
    'get_day_count',
    [{'day_count': 8}, {'day_count': 9}, {'day_count': 10}, {'day_count': 22}], indirect=True
)
def test_rfx_publish_success_over_one_week_correct_dates(client, buyer_user, supplier_domains, suppliers, rfx_brief,
                                                         get_day_count):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today().add(days=get_day_count).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    response = json.loads(res.data)
    assert response['closedAt'] == pendulum.today().add(days=get_day_count).format('%Y-%m-%d')
    assert response['dates']['questions_closing_date'] == (
        pendulum.instance(workday(pendulum.today(), 5)).format('%Y-%m-%d')
    )


def test_rfx_brief_create_failure_as_seller(client, supplier_user):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/brief/rfx', content_type='application/json')
    assert res.status_code == 403


def test_rfx_brief_update_success(client, buyer_user, rfx_brief):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps({
        'closedAt': pendulum.today().add(weeks=2).format('%Y-%m-%d')
    }))
    assert res.status_code == 200
    response = json.loads(res.data)
    assert response['closedAt'] == pendulum.today().add(weeks=2).format('%Y-%m-%d')


def test_rfx_brief_update_failure_closing_date_invalid(client, buyer_user, rfx_brief):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps({
        'publish': True,
        'closedAt': 'baddate'
    }))
    assert res.status_code == 400


def test_rfx_brief_update_failure_unknown_property(client, buyer_user, rfx_brief):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps({
        'publish': True,
        'xxx': 'yyy'
    }))
    assert res.status_code == 400


def test_rfx_validate_location():
    data = {
        'location': [
            'New South Wales',
            'Queensland'
        ]
    }
    valid = RFXDataValidator(data).validate_location()
    assert valid

    data = {
        'location': []
    }
    valid = RFXDataValidator(data).validate_location()
    assert not valid

    data = {
        'location': [
            'Spain'
        ]
    }
    valid = RFXDataValidator(data).validate_location()
    assert not valid


def test_rfx_validate_seller_category(domains):
    data = {
        'sellerCategory': '1'
    }
    valid = RFXDataValidator(data).validate_seller_category()
    assert valid

    data = {
        'sellerCategory': '999'
    }
    valid = RFXDataValidator(data).validate_seller_category()
    assert not valid

    data = {
        'sellerCategory': ''
    }
    valid = RFXDataValidator(data).validate_seller_category()
    assert not valid


def test_rfx_validate_sellers(supplier_domains, suppliers):
    data = {
        'sellerCategory': '1',
        'sellers': {
            '1': {
                'name': 'seller1'
            }
        }
    }
    valid = RFXDataValidator(data).validate_sellers()
    assert valid

    data = {
        'sellerCategory': '1',
        'sellers': {
            '999': {
                'name': 'seller1'
            }
        }
    }
    valid = RFXDataValidator(data).validate_sellers()
    assert not valid

    data = {
        'sellerCategory': '999',
        'sellers': {
            '1': {
                'name': 'seller1'
            }
        }
    }
    valid = RFXDataValidator(data).validate_sellers()
    assert not valid


def test_rfx_validate_response_formats():
    data = {
        'evaluationType': [
            'Response template',
            'Written proposal',
            'Presentation'
        ]
    }
    valid = RFXDataValidator(data).validate_response_formats()
    assert valid

    data = {
        'evaluationType': ''
    }
    valid = RFXDataValidator(data).validate_response_formats()
    assert not valid

    data = {
        'evaluationType': [
            'Response template',
            'Written proposal',
            'ABC'
        ]
    }
    valid = RFXDataValidator(data).validate_response_formats()
    assert not valid


def test_rfx_validate_proposal_type():
    data = {
        'evaluationType': [
            'Written proposal'
        ],
        'proposalType': [
            'Breakdown of costs',
            'Case study',
            'References',
            'Résumés'.decode('utf-8')
        ]
    }
    valid = RFXDataValidator(data).validate_proposal_type()
    assert valid

    data = {
        'evaluationType': [
            'Response template'
        ],
        'proposalType': []
    }
    valid = RFXDataValidator(data).validate_proposal_type()
    assert valid

    data = {
        'evaluationType': [
            'Written proposal'
        ],
        'proposalType': []
    }
    valid = RFXDataValidator(data).validate_proposal_type()
    assert not valid

    data = {
        'evaluationType': [
            'Written proposal'
        ],
        'proposalType': [
            'ABC'
        ]
    }
    valid = RFXDataValidator(data).validate_proposal_type()
    assert not valid


def test_rfx_validate_evaluation_criteria():
    data = {
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
        ]
    }
    valid = RFXDataValidator(data).validate_evaluation_criteria()
    assert valid

    data = {
        'includeWeightings': False,
        'evaluationCriteria': [
            {
                'criteria': 'TEST'
            },
            {
                'criteria': 'TEST 2'
            }
        ]
    }
    valid = RFXDataValidator(data).validate_evaluation_criteria()
    assert valid

    data = {
        'includeWeightings': False,
        'evaluationCriteria': [
            {
                'criteria': ''
            }
        ]
    }
    valid = RFXDataValidator(data).validate_evaluation_criteria()
    assert not valid

    data = {
        'includeWeightings': True,
        'evaluationCriteria': [
            {
                'criteria': 'TEST'
            }
        ]
    }
    valid = RFXDataValidator(data).validate_evaluation_criteria()
    assert not valid

    data = {
        'includeWeightings': True,
        'evaluationCriteria': [
            {
                'criteria': 'TEST',
                'weighting': ''
            }
        ]
    }
    valid = RFXDataValidator(data).validate_evaluation_criteria()
    assert not valid

    data = {
        'includeWeightings': True,
        'evaluationCriteria': [
            {
                'criteria': 'TEST',
                'weighting': '0'
            }
        ]
    }
    valid = RFXDataValidator(data).validate_evaluation_criteria()
    assert not valid

    data = {
        'includeWeightings': True,
        'evaluationCriteria': [
            {
                'criteria': 'TEST',
                'weighting': '80'
            },
            {
                'criteria': 'TEST 2',
                'weighting': '30'
            },
        ]
    }
    valid = RFXDataValidator(data).validate_evaluation_criteria()
    assert not valid


def test_rfx_validate_closed_at():
    data = {
        'closedAt': pendulum.today(tz='Australia/Sydney').add(days=21).format('%Y-%m-%d')
    }
    valid = RFXDataValidator(data).validate_closed_at()
    assert valid

    data = {
        'closedAt': pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')
    }
    valid = RFXDataValidator(data).validate_closed_at()
    assert valid

    data = {
        'closedAt': pendulum.today(tz='Australia/Sydney').add(days=1).format('%Y-%m-%d')
    }
    valid = RFXDataValidator(data).validate_closed_at()
    assert not valid

    data = {
        'closedAt': ''
    }
    valid = RFXDataValidator(data).validate_closed_at()
    assert not valid
