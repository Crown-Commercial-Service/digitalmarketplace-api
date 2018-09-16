import json
import pytest

from app import encryption
from app.models import Brief, Lot, db, utcnow, Supplier, SupplierFramework, Contact, SupplierDomain, User,\
    Framework, UserFramework, AuditEvent
from faker import Faker
from dmapiclient.audit import AuditTypes
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
    assert data['id'] == 1


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
