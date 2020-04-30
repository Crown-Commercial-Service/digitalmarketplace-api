import json

import mock
import pytest

from app import encryption
from app.api.services import audit_service, audit_types
from app.models import User, UserClaim, Team, TeamMember, db, utcnow, Agency


@pytest.fixture()
def agencies(client, app):
    with app.app_context():
        db.session.add(
            Agency(
                id=1,
                name="TEST",
                domain="test.gov.au",
                category="Commonwealth",
                whitelisted=True,
                state="ACT",
                body_type="other",
                reports=True,
                must_join_team=True
            )
        )

        db.session.add(
            Agency(
                id=2,
                name="TEST 2",
                domain="test2.gov.au",
                category="Commonwealth",
                whitelisted=True,
                state="ACT",
                body_type="other",
                reports=True,
                must_join_team=False
            )
        )

        db.session.commit()

        yield db.session.query(Agency).all()


@pytest.fixture()
def users(client, app):
    with app.app_context():
        db.session.add(User(
            id=1,
            email_address='me@digital.gov.au',
            name='Test',
            password=encryption.hashpw('test'),
            active=True,
            role='buyer',
            password_changed_at=utcnow(),
            agency_id=1
        ))

        db.session.add(User(
            id=2,
            email_address='me2@digital.gov.au',
            name='Test',
            password=encryption.hashpw('test'),
            active=True,
            role='buyer',
            password_changed_at=utcnow(),
            agency_id=2
        ))

        db.session.add(User(
            id=3,
            email_address='me3@test.gov.au',
            name='Test User Team Lead',
            password=encryption.hashpw('test'),
            active=True,
            role='buyer',
            password_changed_at=utcnow(),
            agency_id=1
        ))

        db.session.add(User(
            id=4,
            email_address='me4@test.gov.au',
            name='Test User No Team',
            password=encryption.hashpw('test'),
            active=True,
            role='buyer',
            password_changed_at=utcnow(),
            agency_id=1
        ))

        db.session.commit()

        yield db.session.query(User).all()


@pytest.fixture()
def team(client, app):
    with app.app_context():
        db.session.add(Team(
            id=1,
            name='Test Team',
            status='completed'
        ))

        db.session.commit()

        yield db.session.query(Team).all()


@pytest.fixture()
def team_members(client, app, team):
    with app.app_context():
        db.session.add(TeamMember(
            id=1,
            is_team_lead=True,
            team_id=1,
            user_id=3
        ))

        db.session.commit()

        yield db.session.query(Team).all()


@pytest.fixture()
def team_join_requests(client, app, users, team):
    with app.app_context():
        db.session.add(UserClaim(
            id=1,
            token='cf0eead124c3c5defe0b4c5661527edc776d6ed7fb236a8ce2904b536254c6da',
            type='join_team',
            email_address='me4@test.gov.au',
            claimed=False,
            data={
                "team_id": 1,
                "team_name": 'Test Team',
                "agency_id": 1,
                "user_id": 4,
                "user_name": 'Test User No Team',
                "approved": False
            }
        ))

        db.session.add(UserClaim(
            id=2,
            token='cf0eead124c3c5defe0b4c5661527edc776d6ed7fb236a8ce2904b536254c6db',
            type='join_team',
            email_address='me4@test.gov.au',
            claimed=False,
            data={
                "team_id": 1,
                "team_name": 'Test Team',
                "agency_id": 1,
                "user_id": 4,
                "user_name": 'Test User No Team',
                "approved": False
            }
        ))

        db.session.add(UserClaim(
            id=3,
            token='cf0eead124c3c5defe0b4c5661527edc776d6ed7fb236a8ce2904b536254c6dc',
            type='join_team',
            email_address='me4@test.gov.au',
            claimed=False,
            data={
                "team_id": 1,
                "team_name": 'Test Team',
                "agency_id": 1,
                "user_id": 4,
                "user_name": 'Test User No Team',
                "approved": False
            }
        ))

        db.session.commit()

        yield db.session.query(UserClaim).all()


@mock.patch('app.tasks.publish_tasks.team')
def test_audit_event_is_created_when_team_is_created(published_team, client, app, agencies, users):
    with app.app_context():
        client.post('/2/login', data=json.dumps({
            'emailAddress': 'me@digital.gov.au', 'password': 'test'
        }), content_type='application/json')

        response = client.post('/2/team/create', content_type='application/json')
        audit_event = audit_service.find(type=audit_types.create_team.value).first()

        assert audit_event.type == audit_types.create_team.value
        assert audit_event.user == 'me@digital.gov.au'


def test_user_not_in_team_can_not_create_brief_draft(client, app, agencies, users):
    with app.app_context():
        client.post('/2/login', data=json.dumps({
            'emailAddress': 'me@digital.gov.au', 'password': 'test'
        }), content_type='application/json')

        response = client.post('/2/brief/rfx', content_type='application/json')
        response_data = json.loads(response.data)
        assert response.status_code == 403
        assert response_data['message'] == 'You must join a team to perform this action'


def test_user_in_team_can_create_brief_draft(client, app, agencies, users):
    with app.app_context():
        client.post('/2/login', data=json.dumps({
            'emailAddress': 'me2@digital.gov.au', 'password': 'test'
        }), content_type='application/json')

        response = client.post('/2/brief/rfx', content_type='application/json')
        response_data = json.loads(response.data)
        assert response.status_code == 200


def test_user_join_team_request_success(client, app, agencies, team, users, team_members):
    with app.app_context():
        client.post('/2/login', data=json.dumps({
            'emailAddress': 'me4@test.gov.au', 'password': 'test'
        }), content_type='application/json')

        response = client.post('/2/team/1/request-join', content_type='application/json')
        assert response.status_code == 200

        response = client.get('/2/team/join-requests')
        response_data = json.loads(response.data)
        assert response.status_code == 200
        assert 'join_requests' in response_data
        assert len(response_data['join_requests'].keys()) == 1


def test_user_join_team_request_multiple_success(client, app, agencies, team, users, team_members):
    with app.app_context():
        client.post('/2/login', data=json.dumps({
            'emailAddress': 'me4@test.gov.au', 'password': 'test'
        }), content_type='application/json')

        response = client.post('/2/team/1/request-join', content_type='application/json')
        assert response.status_code == 200

        response = client.post('/2/team/1/request-join', content_type='application/json')
        assert response.status_code == 200

        response = client.post('/2/team/1/request-join', content_type='application/json')
        assert response.status_code == 200

        response = client.get('/2/team/join-requests')
        response_data = json.loads(response.data)
        assert response.status_code == 200
        assert 'join_requests' in response_data
        assert '1' in response_data['join_requests']
        assert len(response_data['join_requests']['1']) == 3


def test_user_join_team_request_fails_wrong_agency(client, app, agencies, team, users, team_members):
    with app.app_context():
        client.post('/2/login', data=json.dumps({
            'emailAddress': 'me2@digital.gov.au', 'password': 'test'
        }), content_type='application/json')

        response = client.post('/2/team/1/request-join', content_type='application/json')
        assert response.status_code == 403


def test_user_join_team_request_multiple_all_denied_with_single_deny(
    client, app, agencies, team, users, team_members, team_join_requests
):
    with app.app_context():
        client.post('/2/login', data=json.dumps({
            'emailAddress': 'me3@test.gov.au', 'password': 'test'
        }), content_type='application/json')

        # only deny the first request
        data = {
            'reason': 'just because'
        }
        response = client.post(
            '/2/team/decline-join-request/1/%s' % (team_join_requests[0].token),
            content_type='application/json',
            data=json.dumps(data)
        )
        assert response.status_code == 200

        # check that all requests are denied
        response = client.get('/2/team/join-request/1/%s' % (team_join_requests[0].token))
        response_data = json.loads(response.data)
        assert response.status_code == 404

        response = client.get('/2/team/join-request/1/%s' % (team_join_requests[1].token))
        response_data = json.loads(response.data)
        assert response.status_code == 404

        response = client.get('/2/team/join-request/1/%s' % (team_join_requests[2].token))
        response_data = json.loads(response.data)
        assert response.status_code == 404
