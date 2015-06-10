from tests.app.helpers import BaseApplicationTest
from flask import json
from app.models import AuditEvent, Service
from app import db
from dmutils.audit import AuditTypes
from datetime import datetime

from nose.tools import assert_equal, assert_in


class TestAudits(BaseApplicationTest):

    service = None

    def setup(self):
        super(BaseApplicationTest, self).setup()
        now = datetime.now()
        self.service = Service(
            service_id=1000,
            supplier_id=1,
            updated_at=now,
            status='published',
            created_at=now,
            data={'foo': 'bar'},
            framework_id=1)

    def test_should_get_audit_events(self):
        with self.app.app_context():
            db.session.add(
                AuditEvent(
                    type=AuditTypes.contact_update.value,
                    object=self.service,
                    user='user',
                    data={'request': "data"})
                )
            db.session.commit()

            response = self.client.get('/audits')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
