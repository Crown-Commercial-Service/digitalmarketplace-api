from datetime import datetime, timedelta
import json
import logging

from freezegun import freeze_time
from testfixtures import logcapture

from dmutils.formats import DATETIME_FORMAT

from app.models import AuditEvent, User
from tests.bases import BaseApplicationTest


class TestNotifyCallback(BaseApplicationTest):
    @freeze_time(datetime(2018, 1, 1, 12, 0, 0))
    def notify_data(self, **kwargs):
        data = {
            'id': '32f60997-abe4-4c83-a041-7f3799d256c0',
            'reference': 'my-notification-reference',
            'to': 'my-email@notify.callback.com',
            'status': 'permanent-failure',
            'created_at': (datetime.now()).strftime(DATETIME_FORMAT),
            'sent_at': (datetime.now() + timedelta(seconds=5)).strftime(DATETIME_FORMAT),
            'completed_at': (datetime.now() + timedelta(seconds=10)).strftime(DATETIME_FORMAT),
            'notification_type': 'email',
        }
        data.update(kwargs)
        return data

    def setup(self):
        super().setup()
        self.app.wsgi_app = self.wsgi_app_callbacks

    def test_200_on_notify_callback_root(self):
        response = self.client.get('/callbacks')
        assert response.status_code == 200

    def test_user_account_deactivated_with_log_on_permanent_delivery_failure(self, user_role_supplier):
        notify_data = self.notify_data(to='test+1@digital.gov.uk')

        user = User.query.filter(User.email_address == 'test+1@digital.gov.uk').first()
        assert user.active is True

        with logcapture.LogCapture(names=('flask.app',), level=logging.INFO) as logs:
            response = self.client.post('/callbacks/notify',
                                        data=json.dumps(notify_data),
                                        content_type='application/json')

        assert response.status_code == 200

        user = User.query.filter(User.email_address == 'test+1@digital.gov.uk').first()
        assert user.active is False

        audit_events = AuditEvent.query.filter(AuditEvent.type == 'update_user').all()
        assert len(audit_events) == 1
        assert audit_events[0].data['user'] == {'active': False}
        assert audit_events[0].data['notify_callback_data'] == notify_data

        assert logs.records[1].msg == "User account disabled for -htpNCrT2nn2dCuqWsXwBZDgkP-WQQCYAfPgSw7Rb4A= after " \
                                      "Notify reported permanent delivery failure."

    def test_no_audit_event_if_already_inactive_on_permanent_delivery_failure(self):
        notify_data = self.notify_data()
        response = self.client.post('/callbacks/notify', data=json.dumps(notify_data), content_type='application/json')

        assert response.status_code == 200

        audit_events = AuditEvent.query.all()
        assert len(audit_events) == 0

    def test_error_logged_on_technical_delivery_failure(self):
        notify_data = self.notify_data(status='technical-failure')

        with logcapture.LogCapture(names=('flask.app',), level=logging.WARNING) as logs:
            response = self.client.post('/callbacks/notify',
                                        data=json.dumps(notify_data),
                                        content_type='application/json')

        assert response.status_code == 200
        assert len(logs.records) == 1
        assert logs.records[0].msg == "Notify failed to deliver my-notification-reference to " \
                                      "urpXHRZxYlyjcR9cAeiJkNpfSjZYuw-IOGMbo5x2HTM="
