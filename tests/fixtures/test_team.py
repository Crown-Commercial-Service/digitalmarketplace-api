import json

import mock
import pytest

from app import encryption
from app.api.services import audit_service, audit_types
from app.models import User, db, utcnow


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
            password_changed_at=utcnow()
        ))

        db.session.commit()

        yield db.session.query(User).all()


@mock.patch('app.tasks.publish_tasks.team')
def test_audit_event_is_created_when_team_is_created(published_team, client, app, users):
    with app.app_context():
        client.post('/2/login', data=json.dumps({
            'emailAddress': 'me@digital.gov.au', 'password': 'test'
        }), content_type='application/json')

        response = client.post('/2/team/create', content_type='application/json')
        audit_event = audit_service.find(type=audit_types.create_team.value).first()

        assert audit_event.type == audit_types.create_team.value
        assert audit_event.user == 'me@digital.gov.au'
