from tests.app.helpers import BaseApplicationTest
from flask import json
from datetime import datetime
from app.models import AuditEvent
from app import db
from app.models import Supplier
from dmapiclient.audit import AuditTypes

from nose.tools import assert_equal, assert_in, assert_true, assert_false


class TestMetrics(BaseApplicationTest):
    def test_metrics(self):
        with self.app.app_context():
            response = self.client.get("/metrics",
                                       content_type="application/json")

            data = json.loads(response.get_data(as_text=True))
            assert response.status_code == 200, data

    def test_historical_metrics(self):
        with self.app.app_context():
            response = self.client.get("/metrics/history",
                                       content_type="application/json")

            data = json.loads(response.get_data(as_text=True))
            assert response.status_code == 200, data
