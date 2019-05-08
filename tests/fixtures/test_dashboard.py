import json
import pytest

from app import encryption
from app.models import db, utcnow, Brief, BriefResponse, BriefUser, Framework, Lot, User, UserFramework, WorkOrder
from faker import Faker
from tests.app.helpers import COMPLETE_DIGITAL_SPECIALISTS_BRIEF

fake = Faker()


@pytest.fixture()
def buyer_dashboard_users(app, request):
    with app.app_context():
        db.session.add(User(
            id=1,
            email_address='me@digital.gov.au',
            name=fake.name(),
            password=encryption.hashpw('testpassword'),
            active=True,
            role='buyer',
            password_changed_at=utcnow()
        ))

        db.session.add(User(
            id=2,
            email_address='team@digital.gov.au',
            name=fake.name(),
            password=encryption.hashpw('testpassword'),
            active=True,
            role='buyer',
            password_changed_at=utcnow()
        ))

        db.session.add(User(
            id=3,
            email_address='ceo@digital.gov.au',
            name=fake.name(),
            password=encryption.hashpw('testpassword'),
            active=True,
            role='buyer',
            password_changed_at=utcnow()
        ))

        db.session.flush()

        framework = Framework.query.filter(Framework.slug == "digital-marketplace").first()
        db.session.add(UserFramework(user_id=1, framework_id=framework.id))
        db.session.add(UserFramework(user_id=2, framework_id=framework.id))
        db.session.commit()

        yield User.query.all()


@pytest.fixture()
def buyer_dashboard_briefs(app, request, buyer_dashboard_users, supplier_user):
    with app.app_context():
        for user in buyer_dashboard_users:
            for status in ['draft', 'live', 'closed']:
                brief = Brief(
                    data=COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy(),
                    framework=Framework.query.filter(Framework.slug == "digital-outcomes-and-specialists").first(),
                    lot=Lot.query.filter(Lot.slug == 'digital-specialists').first(),
                    published_at=None,
                    closed_at=None,
                    questions_closed_at=None,
                    withdrawn_at=None
                )
                db.session.add(brief)
                db.session.flush()

                if status == 'live':
                    brief.published_at = utcnow()
                    brief.questions_closed_at = utcnow().add(days=1)
                    brief.closed_at = utcnow().add(days=2)
                elif status == 'closed':
                    brief.published_at = utcnow().subtract(weeks=1)
                    brief.questions_closed_at = utcnow().subtract(days=2)
                    brief.closed_at = utcnow().subtract(days=1)

                brief_user = BriefUser(
                    brief_id=brief.id,
                    user_id=user.id
                )
                db.session.add(brief_user)
                db.session.flush()

                # Link briefs with responses and work orders when they're live or closed
                if status == 'live' or status == 'closed':
                    db.session.add(BriefResponse(
                        brief_id=brief.id,
                        supplier_code=supplier_user.supplier_code,
                        data={}
                    ))

                    db.session.add(WorkOrder(
                        brief_id=brief.id,
                        supplier_code=supplier_user.supplier_code,
                        created_at=utcnow(),
                        data={}
                    ))

        db.session.commit()

        yield Brief.query.all()


def test_buyer_dashboard_my_briefs_route_responds_with_200(client, buyer_dashboard_briefs):
    res = client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')
    assert res.status_code == 200

    response = client.get('/2/dashboard/my/briefs')
    assert response.status_code == 200


def test_buyer_dashboard_my_briefs_response_orders_by_draft_live_then_closed(client, buyer_dashboard_briefs):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/my/briefs')
    items = json.loads(response.data)['items']

    assert items[0]['status'] == 'draft'
    assert items[1]['status'] == 'live'
    assert items[2]['status'] == 'closed'
    assert len(items) == 3


def test_buyer_dashboard_my_briefs_response_includes_count_of_applications(client, buyer_dashboard_briefs):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/my/briefs')
    items = json.loads(response.data)['items']
    assert items[0]['applications'] == 0
    assert items[1]['applications'] == 1
    assert items[2]['applications'] == 1


def test_buyer_dashboard_my_briefs_response_includes_work_order_ids(client, buyer_dashboard_briefs):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/my/briefs')
    items = json.loads(response.data)['items']
    assert items[0]['work_order'] is None
    assert items[1]['work_order'] == 1
    assert items[2]['work_order'] == 2


def test_buyer_dashboard_my_briefs_response_contains_items(client, buyer_dashboard_briefs):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/my/briefs')
    items = json.loads(response.data)['items']
    assert items is not None
    assert 'applications' in items[0]
    assert 'closed_at' in items[0]
    assert 'framework' in items[0]
    assert 'id' in items[0]
    assert 'lot' in items[0]
    assert 'name' in items[0]
    assert 'status' in items[0]
    assert 'work_order' in items[0]


def test_buyer_dashboard_my_briefs_response_contains_organisation(client, agencies, buyer_dashboard_briefs):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/my/briefs')
    organisation = json.loads(response.data)['organisation']

    assert organisation is not None
    assert organisation == 'Digital Transformation Agency'


def test_buyer_dashboard_team_briefs_route_responds_with_200(client, buyer_dashboard_briefs):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/team/briefs')
    assert response.status_code == 200


def test_buyer_dashboard_team_briefs_response_orders_by_live_then_closed(client, buyer_dashboard_briefs):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/team/briefs')
    items = json.loads(response.data)['items']

    assert items[0]['status'] == 'live'
    assert items[1]['status'] == 'live'
    assert items[2]['status'] == 'closed'
    assert items[3]['status'] == 'closed'


def test_buyer_dashboard_team_briefs_response_filters_out_logged_in_user(client, buyer_dashboard_briefs, brief_users):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/team/briefs')
    items = json.loads(response.data)['items']

    brief_users_dict = dict((brief_user.brief_id, brief_user) for brief_user in brief_users)

    for item in items:
        brief_user = brief_users_dict[item['id']]
        assert brief_user.user_id != 1

    assert len(items) == 4


def test_buyer_dashboard_team_briefs_response_contains_items(client, buyer_dashboard_briefs):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/team/briefs')
    items = json.loads(response.data)['items']
    assert items is not None
    assert 'author' in items[0]
    assert 'closed_at' in items[0]
    assert 'framework' in items[0]
    assert 'id' in items[0]
    assert 'lot' in items[0]
    assert 'name' in items[0]
    assert 'status' in items[0]


def test_buyer_dashboard_team_briefs_response_contains_organisation(client, agencies, buyer_dashboard_briefs):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/team/briefs')
    organisation = json.loads(response.data)['organisation']

    assert organisation is not None
    assert organisation == 'Digital Transformation Agency'


def test_buyer_dashboard_team_overview_route_responds_with_200(client, buyer_dashboard_users):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/team/overview')
    assert response.status_code == 200


def test_buyer_dashboard_team_overview_response_orders_names_alphabetically(client, buyer_dashboard_users):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/team/overview')
    items = json.loads(response.data)['items']

    assert items[0]['name'] <= items[1]['name']


def test_buyer_dashboard_team_overview_response_filters_out_logged_in_user(client, buyer_dashboard_users):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/team/overview')
    items = json.loads(response.data)['items']

    for item in items:
        assert item['email'] != 'me@digital.gov.au'


def test_buyer_dashboard_team_overview_response_contains_items(client, buyer_dashboard_users):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/team/overview')
    items = json.loads(response.data)['items']

    assert items is not None
    assert 'email' in items[0]
    assert 'name' in items[0]


def test_buyer_dashboard_team_overview_response_contains_organisation(client, agencies, buyer_dashboard_users):
    client.post('/2/login', data=json.dumps({
        'emailAddress': 'me@digital.gov.au', 'password': 'testpassword'
    }), content_type='application/json')

    response = client.get('/2/dashboard/team/overview')
    organisation = json.loads(response.data)['organisation']

    assert organisation is not None
    assert organisation == 'Digital Transformation Agency'
