# -*- coding: utf-8 -*-
import json
import pytest
import unittest
import mock

from app import encryption
from app.models import Brief, Lot, db, utcnow, Supplier, SupplierFramework, Contact, SupplierDomain, User,\
    Framework, UserFramework, AuditEvent, FrameworkLot, Domain
from app.api.business.validators import RFXDataValidator, ATMDataValidator
from faker import Faker
from dmapiclient.audit import AuditTypes
from workdays import workday
import pendulum

fake = Faker()

specialist_data = {
    'areaOfExpertise': 'Software engineering and Development',
    'attachments': [],
    'budgetRange': '',
    'closedAt': '2019-07-03',
    'contactNumber': '0123456789',
    'contractExtensions': '',
    'contractLength': '1 year',
    'comprehensiveTerms': True,
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
    'evaluationType': [
        'Responses to selection criteria',
        'Résumés'
    ],
    'includeWeightingsEssential': False,
    'includeWeightingsNiceToHave': False,
    'internalReference': '',
    'location': [
        'Australian Capital Territory'
    ],
    'maxRate': '123',
    'niceToHaveRequirements': [
        {
            'criteria': 'Code review',
            'weighting': '0'
        }
    ],
    'numberOfSuppliers': '3',
    'openTo': 'all',
    'organisation': 'Digital Transformation Agency',
    'preferredFormatForRates': 'dailyRate',
    'securityClearance': 'noneRequired',
    'securityClearanceCurrent': '',
    'securityClearanceObtain': '',
    'securityClearanceOther': '',
    'sellers': {},
    'sellerCategory': '6',
    'startDate': pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d'),
    'summary': 'asdf',
    'title': 'Developer'
}


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
                        "indemnity": {
                            "filename": "4.pdf",
                            "expiry": pendulum.tomorrow().date().to_date_string()
                        },
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
    domains = Domain.query.all()
    with app.app_context():
        for s in suppliers:
            for domain in domains:
                db.session.add(SupplierDomain(
                    supplier_id=s.id,
                    domain_id=domain.id,
                    status='assessed',
                    price_status='approved'
                ))
                db.session.commit()
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
@pytest.mark.parametrize(
    'specialist_brief',
    [{
        'data': specialist_data,
        'published_at': pendulum.yesterday(tz='Australia/Sydney').subtract(days=1).format('%Y-%m-%d')
    }], indirect=True
)
def test_create_new_brief_response(brief_response,
                                   client,
                                   supplier_user,
                                   supplier_domains,
                                   specialist_brief,
                                   suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/brief/1/respond')
    assert res.status_code == 201
    assert brief_response.delay.called is True


@mock.patch('app.tasks.publish_tasks.brief_response')
@pytest.mark.parametrize(
    'specialist_brief',
    [{
        'data': specialist_data,
        'published_at': pendulum.yesterday(tz='Australia/Sydney').subtract(days=1).format('%Y-%m-%d')
    }], indirect=True
)
def test_save_draft_brief_response(brief_response,
                                   client,
                                   supplier_user,
                                   supplier_domains,
                                   specialist_brief,
                                   suppliers):
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
            'submit': False,
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
    data = json.loads(res.get_data(as_text=True))
    assert data['status'] == 'draft'


@mock.patch('app.tasks.publish_tasks.brief_response')
@pytest.mark.parametrize(
    'specialist_brief',
    [{
        'data': specialist_data,
        'published_at': pendulum.yesterday(tz='Australia/Sydney').subtract(days=1).format('%Y-%m-%d')
    }], indirect=True
)
def test_create_brief_response_creates_an_audit_event(brief_response, client, supplier_user, supplier_domains,
                                                      specialist_brief, suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/brief/1/respond')
    assert res.status_code == 201
    assert brief_response.delay.called is True

    audit_events = AuditEvent.query.filter(
        AuditEvent.type == AuditTypes.create_brief_response.value
    ).all()

    assert len(audit_events) == 1
    assert audit_events[0].data['briefResponseId'] == 1


@mock.patch('app.tasks.publish_tasks.brief_response')
@pytest.mark.parametrize(
    'specialist_brief',
    [{
        'data': specialist_data,
        'published_at': pendulum.yesterday(tz='Australia/Sydney').subtract(days=1).format('%Y-%m-%d')
    }], indirect=True
)
def test_cannot_respond_to_a_brief_more_than_three_times_from_the_same_supplier(brief_response,
                                                                                client, supplier_user,
                                                                                supplier_domains,
                                                                                specialist_brief, suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    for i in range(0, 3):
        res = client.post('/2/brief/1/respond')
        assert res.status_code == 201
        assert brief_response.delay.called is True

    res = client.post('/2/brief/1/respond')
    assert res.status_code == 400
    assert 'Supplier has reached the permitted amount of draft/submitted responses for this opportunity' in\
        res.get_data(as_text=True)


@pytest.mark.parametrize(
    'specialist_brief',
    [{
        'data': specialist_data,
        'published_at': pendulum.yesterday(tz='Australia/Sydney').subtract(days=1).format('%Y-%m-%d')
    }], indirect=True
)
def test_cannot_respond_to_a_brief_with_wrong_number_of_essential_reqs(client, supplier_user,
                                                                       supplier_domains, specialist_brief,
                                                                       suppliers):
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
            'specialistGivenNames': 'a',
            'specialistSurname': 'b',
            'previouslyWorked': 'x',
            'visaStatus': 'y',
            'essentialRequirements': [
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
    assert res.status_code == 400
    assert 'Essential requirements must be completed' in res.get_data(as_text=True)


@mock.patch('app.tasks.publish_tasks.brief_response')
@pytest.mark.parametrize(
    'specialist_brief',
    [{
        'data': specialist_data,
        'published_at': pendulum.yesterday(tz='Australia/Sydney').subtract(days=1).format('%Y-%m-%d')
    }], indirect=True
)
def test_create_brief_response_success_with_audit_exception(brief_response,
                                                            client, supplier_user, supplier_domains,
                                                            specialist_brief, suppliers):
    audit_event = mock.patch('app.api.views.briefs.audit_service')
    audit_event.side_effect = Exception('Test')

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
    data = json.loads(res.get_data(as_text=True))
    assert res.status_code == 200
    assert brief_response.delay.called is True


@pytest.mark.parametrize(
    'specialist_brief',
    [{
        'data': specialist_data,
        'published_at': pendulum.yesterday(tz='Australia/Sydney').subtract(days=1).format('%Y-%m-%d')
    }], indirect=True
)
def test_create_brief_response_fail_with_incorrect_attachment(client, supplier_user, supplier_domains,
                                                              specialist_brief, suppliers):
    audit_event = mock.patch('app.api.views.briefs.audit_service')
    audit_event.side_effect = Exception('Test')

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
            'attachedDocumentURL': [[{}]]
        }),
        content_type='application/json'
    )
    assert res.status_code == 400

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
            'attachedDocumentURL': ['test.exe']
        }),
        content_type='application/json'
    )
    assert res.status_code == 400


@pytest.mark.parametrize(
    'specialist_brief',
    [{
        'data': specialist_data,
        'published_at': pendulum.yesterday(tz='Australia/Sydney').subtract(days=1).format('%Y-%m-%d')
    }], indirect=True
)
@mock.patch('app.tasks.publish_tasks.brief_response')
def test_get_brief(brief_response, client, supplier_user, supplier_domains, specialist_brief, suppliers):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/brief/1/respond')
    assert res.status_code == 201
    assert brief_response.delay.called is True

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
def test_rfx_field_access_as_owner(brief, client, supplier_domains, suppliers, buyer_user, rfx_brief, rfx_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    response = json.loads(res.data)
    assert brief.delay.called is True

    res = client.get('/2/brief/1')
    response = json.loads(res.data)
    assert response['brief']['industryBriefing'] == 'TEST'
    assert response['brief']['attachments'] == ['TEST3.pdf']
    assert response['brief']['sellers'] == {'1': {'name': 'Test Supplier1'}}
    assert response['brief']['evaluationType'] == ['Response template', 'Written proposal']
    assert response['brief']['proposalType'] == ['Breakdown of costs', u'R\xe9sum\xe9s']
    assert response['brief']['requirementsDocument'] == ['TEST.pdf']
    assert response['brief']['responseTemplate'] == ['TEST2.pdf']
    assert response['brief']['contactNumber'] == '0263635544'


@mock.patch('app.tasks.publish_tasks.brief')
def test_rfx_field_access_as_invited_seller(brief, client, supplier_domains, suppliers,
                                            buyer_user, rfx_brief, rfx_data, supplier_user):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')
    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert brief.delay.called is True

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


@mock.patch('app.tasks.publish_tasks.brief')
def test_rfx_field_access_as_non_invited_seller(brief, client, supplier_domains, suppliers, buyer_user, rfx_brief,
                                                supplier_user, rfx_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')
    data['sellers'] = {'2': 'Test Supplier2'}
    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert brief.delay.called is True

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


@mock.patch('app.tasks.publish_tasks.brief')
def test_rfx_field_access_as_anonymous_user(brief, client, supplier_domains, suppliers, buyer_user, rfx_brief,
                                            rfx_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')
    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert brief.delay.called is True

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


@mock.patch('app.tasks.publish_tasks.brief')
def test_rfx_publish_success_2_days_correct_dates(brief, client, supplier_domains, suppliers, buyer_user, rfx_brief,
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

    response = json.loads(res.data)
    assert response['closedAt'] == pendulum.today().add(days=2).format('%Y-%m-%d')
    question_closing_date = pendulum.instance(workday(pendulum.today().add(days=2), -1)).format('%Y-%m-%d')
    if question_closing_date > response['closedAt']:
        question_closing_date = pendulum.today().format('%Y-%m-%d')
    if pendulum.today() > question_closing_date:
        question_closing_date = pendulum.today()
    assert response['dates']['questions_closing_date'] == question_closing_date


def test_rfx_publish_failure_next_day(client, buyer_user, supplier_domains, suppliers, rfx_brief, rfx_data):
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


@mock.patch('app.tasks.publish_tasks.brief')
@pytest.mark.parametrize(
    'get_day_count',
    [{'day_count': 2}, {'day_count': 3}], indirect=True
)
def test_rfx_publish_success_3_days_and_under_correct_dates(brief, client, buyer_user,
                                                            supplier_domains, suppliers, rfx_brief,
                                                            get_day_count, rfx_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today().add(days=get_day_count).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(rfx_data))
    assert res.status_code == 200
    assert brief.delay.called is True

    response = json.loads(res.data)
    assert response['closedAt'] == pendulum.today().add(days=get_day_count).format('%Y-%m-%d')
    question_closing_date = pendulum.instance(workday(pendulum.today().add(days=get_day_count), -1)).format('%Y-%m-%d')
    if question_closing_date > response['closedAt']:
        question_closing_date = response['closedAt']
    if pendulum.today() > question_closing_date:
        question_closing_date = pendulum.today()
    assert response['dates']['questions_closing_date'] == question_closing_date


@mock.patch('app.tasks.publish_tasks.brief')
@pytest.mark.parametrize(
    'get_day_count',
    [{'day_count': 4}, {'day_count': 5}, {'day_count': 10}, {'day_count': 22}, {'day_count': 36}], indirect=True
)
def test_rfx_publish_success_over_3_days_correct_dates(brief, client, buyer_user,
                                                       supplier_domains, suppliers, rfx_brief,
                                                       get_day_count, rfx_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today().add(days=get_day_count).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    assert brief.delay.called is True

    response = json.loads(res.data)
    assert response['closedAt'] == pendulum.today().add(days=get_day_count).format('%Y-%m-%d')
    assert response['dates']['questions_closing_date'] == (
        pendulum.instance(workday(pendulum.today().add(days=get_day_count), -2)).format('%Y-%m-%d')
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


@mock.patch('app.tasks.publish_tasks.brief')
def test_atm_brief_create_success_and_visible_to_author(brief, client, buyer_user):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/brief/atm', content_type='application/json')
    assert res.status_code == 200

    response = json.loads(res.data)
    assert response['id'] == 1

    res = client.get('/2/brief/1', content_type='application/json')
    assert res.status_code == 200


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
        'requestMoreInfo': 'yes',
        'evaluationType': [
            'References',
            'Case study',
        ],
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
def test_atm_field_access_as_owner(brief, client, supplier_domains, suppliers, buyer_user, atm_brief, atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    response = json.loads(res.data)

    res = client.get('/2/brief/1')
    response = json.loads(res.data)
    assert response['brief']['industryBriefing'] == 'TEST'
    assert response['brief']['attachments'] == ['TEST3.pdf']
    assert response['brief']['evaluationType'] == ['References', 'Case study']
    assert response['brief']['timeframeConstraints'] == 'TEST'
    assert response['brief']['backgroundInformation'] == 'TEST'
    assert response['brief']['outcome'] == 'TEST'
    assert response['brief']['endUsers'] == 'TEST'
    assert response['brief']['workAlreadyDone'] == 'TEST'


@mock.patch('app.tasks.publish_tasks.brief')
def test_atm_field_access_as_seller_open_to_all(brief, client, supplier_domains, suppliers, buyer_user, atm_brief,
                                                supplier_user, atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['openTo'] = 'all'
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
    assert response['brief']['evaluationType'] == ['References', 'Case study']
    assert response['brief']['timeframeConstraints'] == 'TEST'
    assert response['brief']['backgroundInformation'] == 'TEST'
    assert response['brief']['outcome'] == 'TEST'
    assert response['brief']['endUsers'] == 'TEST'
    assert response['brief']['workAlreadyDone'] == 'TEST'


@mock.patch('app.tasks.publish_tasks.brief')
def test_atm_field_access_as_anonymous_user(brief, client, supplier_domains, suppliers, buyer_user, atm_brief,
                                            atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')
    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))

    res = client.get('/2/logout')
    res = client.get('/2/brief/1')
    response = json.loads(res.data)
    assert response['brief']['industryBriefing'] == ''
    assert response['brief']['attachments'] == []
    assert response['brief']['evaluationType'] == []
    assert response['brief']['timeframeConstraints'] == ''
    assert response['brief']['backgroundInformation'] == ''
    assert response['brief']['outcome'] == ''
    assert response['brief']['endUsers'] == ''
    assert response['brief']['workAlreadyDone'] == ''


@mock.patch('app.tasks.publish_tasks.brief')
def test_atm_publish_success_2_days_correct_dates(brief, client, supplier_domains, suppliers, buyer_user, atm_brief,
                                                  atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    response = json.loads(res.data)
    assert response['closedAt'] == pendulum.today().add(days=2).format('%Y-%m-%d')
    question_closing_date = pendulum.instance(workday(pendulum.today().add(days=2), -1)).format('%Y-%m-%d')
    if question_closing_date > response['closedAt']:
        question_closing_date = pendulum.today().format('%Y-%m-%d')
    if pendulum.today() > question_closing_date:
        question_closing_date = pendulum.today()
    assert response['dates']['questions_closing_date'] == question_closing_date


@mock.patch('app.tasks.publish_tasks.brief')
def test_atm_publish_failure_next_day(brief, client, buyer_user, supplier_domains, suppliers, atm_brief, atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
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
    [{'day_count': 2}, {'day_count': 3}], indirect=True
)
@mock.patch('app.tasks.publish_tasks.brief')
def test_atm_publish_success_3_days_and_under_correct_dates(brief, client, buyer_user, supplier_domains, suppliers,
                                                            atm_brief, get_day_count, atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['closedAt'] = pendulum.today().add(days=get_day_count).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(atm_data))
    assert res.status_code == 200
    response = json.loads(res.data)
    assert response['closedAt'] == pendulum.today().add(days=get_day_count).format('%Y-%m-%d')
    question_closing_date = pendulum.instance(workday(pendulum.today().add(days=get_day_count), -1)).format('%Y-%m-%d')
    if question_closing_date > response['closedAt']:
        question_closing_date = response['closedAt']
    if pendulum.today() > question_closing_date:
        question_closing_date = pendulum.today()
    assert response['dates']['questions_closing_date'] == question_closing_date


@pytest.mark.parametrize(
    'get_day_count',
    [{'day_count': 4}, {'day_count': 5}, {'day_count': 10}, {'day_count': 22}, {'day_count': 36}], indirect=True
)
@mock.patch('app.tasks.publish_tasks.brief')
def test_atm_publish_success_over_3_days_correct_dates(brief, client, buyer_user, supplier_domains, suppliers,
                                                       atm_brief, get_day_count, atm_data):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    data = atm_data
    data['publish'] = True
    data['closedAt'] = pendulum.today().add(days=get_day_count).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))
    assert res.status_code == 200
    response = json.loads(res.data)
    assert response['closedAt'] == pendulum.today().add(days=get_day_count).format('%Y-%m-%d')
    assert response['dates']['questions_closing_date'] == (
        pendulum.instance(workday(pendulum.today().add(days=get_day_count), -2)).format('%Y-%m-%d')
    )


def test_atm_brief_create_failure_as_seller(client, supplier_user):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'j@examplecompany.biz', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.post('/2/brief/atm', content_type='application/json')
    assert res.status_code == 403


@mock.patch('app.tasks.publish_tasks.brief')
def test_atm_brief_update_success(brief, client, buyer_user, atm_brief):
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


@mock.patch('app.tasks.publish_tasks.brief')
def test_atm_brief_update_failure_closing_date_invalid(brief, client, buyer_user, atm_brief):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps({
        'publish': True,
        'closedAt': 'baddate'
    }))
    assert res.status_code == 400


@mock.patch('app.tasks.publish_tasks.brief')
def test_atm_brief_update_failure_unknown_property(brief, client, buyer_user, atm_brief):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')
    assert res.status_code == 200

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps({
        'publish': True,
        'xxx': 'yyy'
    }))
    assert res.status_code == 400


def test_atm_validate_location():
    data = {
        'location': [
            'New South Wales',
            'Queensland'
        ]
    }
    valid = ATMDataValidator(data).validate_location()
    assert valid

    data = {
        'location': []
    }
    valid = ATMDataValidator(data).validate_location()
    assert not valid

    data = {
        'location': [
            'Spain'
        ]
    }
    valid = ATMDataValidator(data).validate_location()
    assert not valid


def test_atm_validate_seller_category(domains):
    data = {
        'sellerCategory': '',
        'openTo': 'all'
    }
    valid = ATMDataValidator(data).validate_seller_category()
    assert valid

    data = {
        'sellerCategory': '1',
        'openTo': 'category'
    }
    valid = ATMDataValidator(data).validate_seller_category()
    assert valid

    data = {
        'sellerCategory': '1',
        'openTo': 'all'
    }
    valid = ATMDataValidator(data).validate_seller_category()
    assert not valid


def test_atm_validate_response_formats():
    data = {
        'requestMoreInfo': 'yes',
        'evaluationType': [
            'References',
            'Case study',
            'Presentation',
        ]
    }
    valid = ATMDataValidator(data).validate_response_formats()
    assert valid

    data = {
        'requestMoreInfo': 'no',
        'evaluationType': ''
    }
    valid = ATMDataValidator(data).validate_response_formats()
    assert valid

    data = {
        'requestMoreInfo': 'no',
        'evaluationType': [
            'References',
            'Case study',
            'Prototype'
            'ABC'
        ]
    }
    valid = ATMDataValidator(data).validate_response_formats()
    assert not valid

    data = {
        'requestMoreInfo': 'yes',
        'evaluationType': []
    }
    valid = ATMDataValidator(data).validate_response_formats()
    assert not valid

    data = {
        'requestMoreInfo': 'xxx',
        'evaluationType': ''
    }
    valid = ATMDataValidator(data).validate_response_formats()
    assert not valid


def test_atm_validate_evaluation_criteria():
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
    valid = ATMDataValidator(data).validate_evaluation_criteria()
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
    valid = ATMDataValidator(data).validate_evaluation_criteria()
    assert valid

    data = {
        'includeWeightings': False,
        'evaluationCriteria': [
            {
                'criteria': ''
            }
        ]
    }
    valid = ATMDataValidator(data).validate_evaluation_criteria()
    assert not valid

    data = {
        'includeWeightings': True,
        'evaluationCriteria': [
            {
                'criteria': 'TEST'
            }
        ]
    }
    valid = ATMDataValidator(data).validate_evaluation_criteria()
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
    valid = ATMDataValidator(data).validate_evaluation_criteria()
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
    valid = ATMDataValidator(data).validate_evaluation_criteria()
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
    valid = ATMDataValidator(data).validate_evaluation_criteria()
    assert not valid


def test_atm_validate_closed_at():
    data = {
        'closedAt': pendulum.today(tz='Australia/Sydney').add(days=21).format('%Y-%m-%d')
    }
    valid = ATMDataValidator(data).validate_closed_at()
    assert valid

    data = {
        'closedAt': pendulum.today(tz='Australia/Sydney').add(days=2).format('%Y-%m-%d')
    }
    valid = ATMDataValidator(data).validate_closed_at()
    assert valid

    data = {
        'closedAt': pendulum.today(tz='Australia/Sydney').add(days=1).format('%Y-%m-%d')
    }
    valid = ATMDataValidator(data).validate_closed_at()
    assert not valid

    data = {
        'closedAt': ''
    }
    valid = ATMDataValidator(data).validate_closed_at()
    assert not valid


@pytest.mark.parametrize('opportunity_type', ['atm', 'rfx', 'training', 'specialist'])
def test_buyer_can_not_create_draft_opportunity_without_permission(client, buyer_user, opportunity_type,
                                                                   teams, team_members):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    res = client.post('/2/brief/{}'.format(opportunity_type), content_type='application/json')
    assert res.status_code == 403


@pytest.mark.parametrize('opportunity_type', ['atm', 'rfx', 'training', 'specialist'])
def test_buyer_can_create_draft_opportunity_with_permission(client, buyer_user, opportunity_type, teams, team_members,
                                                            create_drafts_permission):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    res = client.post('/2/brief/{}'.format(opportunity_type), content_type='application/json')
    assert res.status_code == 200


def test_buyer_can_not_publish_atm_opportunity_without_permission(client, buyer_user, atm_brief, atm_data,
                                                                  teams, team_members):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    data = atm_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))

    assert res.status_code == 403


@mock.patch('app.tasks.publish_tasks.brief')
def test_buyer_can_publish_atm_opportunity_with_permission(brief, client, buyer_user, atm_brief, atm_data, teams,
                                                           team_members, publish_opportunities_permission):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    data = atm_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))

    assert res.status_code == 200


def test_buyer_can_not_publish_rfx_opportunity_without_permission(client, buyer_user, rfx_brief, rfx_data,
                                                                  teams, team_members):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))

    assert res.status_code == 403


@mock.patch('app.tasks.publish_tasks.brief')
def test_buyer_can_publish_rfx_opportunity_with_permission(brief, client, buyer_user, rfx_brief, rfx_data,
                                                           supplier_domains, suppliers, teams, team_members,
                                                           publish_opportunities_permission):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    data = rfx_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))

    assert res.status_code == 200


def test_buyer_can_not_publish_specialist_opportunity_without_permission(client, buyer_user, specialist_brief,
                                                                         specialist_data, teams, team_members):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    data = specialist_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))

    assert res.status_code == 403


@mock.patch('app.tasks.publish_tasks.brief')
def test_buyer_can_publish_specialist_opportunity_with_permission(brief, client, buyer_user, specialist_brief,
                                                                  specialist_data, teams, team_members,
                                                                  publish_opportunities_permission):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'test'
    }), content_type='application/json')

    data = specialist_data
    data['publish'] = True
    data['closedAt'] = pendulum.today(tz='Australia/Sydney').add(days=14).format('%Y-%m-%d')

    res = client.patch('/2/brief/1', content_type='application/json', data=json.dumps(data))

    assert res.status_code == 200
