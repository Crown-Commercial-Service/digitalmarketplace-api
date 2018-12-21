from tests.app.helpers import BaseApplicationTest
from flask import json
from datetime import datetime
from app.models import AuditEvent
from app import db
from app.models import Supplier
from dmapiclient.audit import AuditTypes

from nose.tools import assert_equal, assert_in, assert_true, assert_false


class TestAuditEvents(BaseApplicationTest):
    @staticmethod
    def audit_event(user, type, db_object=None):
        return AuditEvent(
            audit_type=type,
            db_object=db_object,
            user=user,
            data={'request': "data"}
        )

    def add_audit_events(self, number, type=AuditTypes.supplier_update, db_object=None):
        with self.app.app_context():
            for i in range(number):
                db.session.add(
                    self.audit_event(i, type, db_object)
                )
            db.session.commit()

    def add_audit_events_with_db_object(self):
        self.setup_dummy_suppliers(3)
        with self.app.app_context():
            suppliers = Supplier.query.all()
            for supplier in suppliers:
                event = AuditEvent(AuditTypes.contact_update, "rob", {}, supplier)
                db.session.add(event)
            db.session.commit()

    def test_should_get_audit_event(self):
        self.add_audit_events(1)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['auditEvents']), 1)
        assert_equal(data['auditEvents'][0]['user'], '0')
        assert_equal(data['auditEvents'][0]['data']['request'], 'data')

    def test_should_get_audit_events_sorted(self):
        self.add_audit_events(5)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(data['auditEvents'][0]['user'], '0')
        assert_equal(data['auditEvents'][4]['user'], '4')

        response = self.client.get('/audit-events?latest_first=true')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(data['auditEvents'][0]['user'], '4')
        assert_equal(data['auditEvents'][4]['user'], '0')

    def test_should_get_audit_event_using_audit_date(self):
        today = datetime.utcnow().strftime("%Y-%m-%d")

        self.add_audit_events(1)
        response = self.client.get('/audit-events?audit-date={}'.format(today))
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['auditEvents']), 1)
        assert_equal(data['auditEvents'][0]['user'], '0')
        assert_equal(data['auditEvents'][0]['data']['request'], 'data')

    def test_should_not_get_audit_event_for_date_with_no_events(self):
        self.add_audit_events(1)
        response = self.client.get('/audit-events?audit-date=2000-01-01')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['auditEvents']), 0)

    def test_should_reject_invalid_audit_dates(self):
        self.add_audit_events(1)
        response = self.client.get('/audit-events?audit-date=invalid')

        assert_equal(response.status_code, 400)

    def test_should_get_audit_event_by_type(self):
        self.add_audit_events(1, AuditTypes.contact_update)
        self.add_audit_events(1, AuditTypes.supplier_update)
        response = self.client.get('/audit-events?audit-type=contact_update')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['auditEvents']), 1)
        assert_equal(data['auditEvents'][0]['user'], '0')
        assert_equal(data['auditEvents'][0]['type'], 'contact_update')
        assert_equal(data['auditEvents'][0]['data']['request'], 'data')

    def test_should_get_audit_event_by_object(self):
        self.add_audit_events_with_db_object()

        response = self.client.get('/audit-events?object-type=suppliers&object-id=1')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['auditEvents']), 1)
        assert_equal(data['auditEvents'][0]['user'], 'rob')

    def test_get_audit_event_for_missing_object_returns_404(self):
        self.add_audit_events_with_db_object()

        response = self.client.get('/audit-events?object-type=suppliers&object-id=100000')
        json.loads(response.get_data())

        assert_equal(response.status_code, 404)

    def test_should_only_get_audit_event_with_correct_object_type(self):
        self.add_audit_events_with_db_object()

        with self.app.app_context():
            # Create a second AuditEvent with the same object_id but with a
            # different object_type to check that we're not filtering based
            # on object_id only
            supplier = Supplier.query.filter(Supplier.code == 1).first()
            event = AuditEvent(
                audit_type=AuditTypes.supplier_update,
                db_object=supplier,
                user='not rob',
                data={'request': "data"}
            )
            event.object_type = 'Service'

            db.session.add(event)
            db.session.commit()

        response = self.client.get('/audit-events?object-type=suppliers&object-id=1')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['auditEvents']), 1)
        assert_equal(data['auditEvents'][0]['user'], 'rob')

    def test_should_reject_invalid_object_type(self):
        self.add_audit_events_with_db_object()

        response = self.client.get('/audit-events?object-type=invalid&object-id=1')

        assert_equal(response.status_code, 400)

    def test_should_reject_object_type_if_no_object_id_is_given(self):
        self.add_audit_events_with_db_object()

        response = self.client.get('/audit-events?object-type=suppliers')

        assert_equal(response.status_code, 400)

    def test_should_reject_object_id_if_no_object_type_is_given(self):
        self.add_audit_events_with_db_object()

        response = self.client.get('/audit-events?object-id=1')

        assert_equal(response.status_code, 400)

    def test_should_get_audit_events_ordered_by_created_date(self):
        self.add_audit_events(5)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['auditEvents']), 5)

        assert_equal(data['auditEvents'][4]['user'], '4')
        assert_equal(data['auditEvents'][3]['user'], '3')
        assert_equal(data['auditEvents'][2]['user'], '2')
        assert_equal(data['auditEvents'][1]['user'], '1')
        assert_equal(data['auditEvents'][0]['user'], '0')

    def test_should_reject_invalid_page(self):
        self.add_audit_events(1)
        response = self.client.get('/audit-events?page=invalid')

        assert_equal(response.status_code, 400)

    def test_should_reject_missing_page(self):
        self.add_audit_events(1)
        response = self.client.get('/audit-events?page=')

        assert_equal(response.status_code, 400)

    def test_should_return_404_if_page_exceeds_results(self):
        self.add_audit_events(7)
        response = self.client.get('/audit-events?page=100')

        assert_equal(response.status_code, 404)

    def test_should_get_audit_events_paginated(self):
        self.add_audit_events(7)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['auditEvents']), 5)
        next_link = data['links']['next']
        assert_in('page=2', next_link)
        assert_equal(data['auditEvents'][0]['user'], '0')
        assert_equal(data['auditEvents'][1]['user'], '1')
        assert_equal(data['auditEvents'][2]['user'], '2')
        assert_equal(data['auditEvents'][3]['user'], '3')
        assert_equal(data['auditEvents'][4]['user'], '4')

    def test_paginated_audit_events_page_two(self):
        self.add_audit_events(7)

        response = self.client.get('/audit-events?page=2')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['auditEvents']), 2)
        prev_link = data['links']['prev']
        assert_in('page=1', prev_link)
        assert_false('next' in data['links'])
        assert_equal(data['auditEvents'][0]['user'], '5')
        assert_equal(data['auditEvents'][1]['user'], '6')

    def test_paginated_audit_with_custom_page_size(self):
        self.add_audit_events(12)
        response = self.client.get('/audit-events?per_page=10')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['auditEvents']), 10)

    def test_paginated_audit_with_custom_page_size_and_specified_page(self):
        self.add_audit_events(12)
        response = self.client.get('/audit-events?page=2&per_page=10')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['auditEvents']), 2)
        prev_link = data['links']['prev']
        assert_in('page=1', prev_link)
        assert_false('next' in data['links'])

    def test_paginated_audit_with_invalid_custom_page_size(self):
        self.add_audit_events(1)
        response = self.client.get('/audit-events?per_page=foo')
        assert_equal(response.status_code, 400)

    def test_reject_invalid_audit_id_on_acknowledgement(self):
        res = self.client.post(
            '/audit-events/invalid-id!/acknowledge',
            data=json.dumps({'key': 'value'}),
            content_type='application/json')

        assert_equal(res.status_code, 404)

    def test_reject_if_no_updater_details_on_acknowledgement(self):
        res = self.client.post(
            '/audit-events/123/acknowledge',
            data={},
            content_type='application/json')

        assert_equal(res.status_code, 400)

    def test_should_update_audit_event(self):
        self.add_audit_events(1)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        res = self.client.post(
            '/audit-events/{}/acknowledge'.format(
                data['auditEvents'][0]['id']
            ),
            data=json.dumps({'updated_by': 'tests'}),
            content_type='application/json')
        # re-fetch to get updated data
        new_response = self.client.get('/audit-events')
        new_data = json.loads(new_response.get_data())
        assert_equal(res.status_code, 200)
        assert_equal(new_data['auditEvents'][0]['acknowledged'], True)
        assert_equal(new_data['auditEvents'][0]['acknowledgedBy'], 'tests')

    def test_should_get_all_audit_events(self):
        self.add_audit_events(2)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        res = self.client.post(
            '/audit-events/{}/acknowledge'.format(
                data['auditEvents'][0]['id']
            ),
            data=json.dumps({'updated_by': 'tests'}),
            content_type='application/json')
        # re-fetch to get updated data
        new_response = self.client.get('/audit-events')
        new_data = json.loads(new_response.get_data())
        assert_equal(res.status_code, 200)
        assert_equal(len(new_data['auditEvents']), 2)

        # all should return both
        new_response = self.client.get('/audit-events?acknowledged=all')
        new_data = json.loads(new_response.get_data())
        assert_equal(res.status_code, 200)
        assert_equal(len(new_data['auditEvents']), 2)

    def test_should_get_only_acknowledged_audit_events(self):
        self.add_audit_events(2)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        res = self.client.post(
            '/audit-events/{}/acknowledge'.format(
                data['auditEvents'][0]['id']
            ),
            data=json.dumps({'updated_by': 'tests'}),
            content_type='application/json')
        # re-fetch to get updated data
        new_response = self.client.get(
            '/audit-events?acknowledged=true'
        )
        new_data = json.loads(new_response.get_data())
        assert_equal(res.status_code, 200)
        assert_equal(len(new_data['auditEvents']), 1)
        assert_equal(
            new_data['auditEvents'][0]['id'],
            data['auditEvents'][0]['id'])

    def test_should_get_only_not_acknowledged_audit_events(self):
        self.add_audit_events(2)
        response = self.client.get('/audit-events')
        data = json.loads(response.get_data())

        res = self.client.post(
            '/audit-events/{}/acknowledge'.format(
                data['auditEvents'][0]['id']
            ),
            data=json.dumps({'updated_by': 'tests'}),
            content_type='application/json')
        # re-fetch to get updated data
        new_response = self.client.get(
            '/audit-events?acknowledged=false'
        )
        new_data = json.loads(new_response.get_data())
        assert_equal(res.status_code, 200)
        assert_equal(len(new_data['auditEvents']), 1)
        assert_equal(
            new_data['auditEvents'][0]['id'],
            data['auditEvents'][1]['id']
        )


class TestCreateAuditEvent(BaseApplicationTest):
    @staticmethod
    def audit_event():
        audit_event = {
            "type": "register_framework_interest",
            "user": "A User",
            "data": {
                "Key": "value"
            },
        }

        return audit_event

    def audit_event_with_db_object(self):
        audit_event = self.audit_event()
        self.setup_dummy_suppliers(1)
        audit_event['objectType'] = 'suppliers'
        audit_event['objectId'] = 0

        return audit_event

    def test_create_an_audit_event(self):
        audit_event = self.audit_event()

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')

        assert_equal(res.status_code, 201)

    def test_create_an_audit_event_with_an_associated_object(self):
        audit_event = self.audit_event_with_db_object()

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')

        assert_equal(res.status_code, 201)

    def test_create_audit_event_with_no_user(self):
        audit_event = self.audit_event()
        del audit_event['user']

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')

        assert_equal(res.status_code, 201)

    def test_should_fail_if_no_type_is_given(self):
        audit_event = self.audit_event()
        del audit_event['type']

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert_equal(res.status_code, 400)
        assert_true(data['error'].startswith("Invalid JSON"))

    def test_should_fail_if_an_invalid_type_is_given(self):
        audit_event = self.audit_event()
        audit_event['type'] = 'invalid'

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert_equal(res.status_code, 400)
        assert_equal(data['error'], "invalid audit type supplied")

    def test_should_fail_if_no_data_is_given(self):
        audit_event = self.audit_event()
        del audit_event['data']

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert_equal(res.status_code, 400)
        assert_true(data['error'].startswith("Invalid JSON"))

    def test_should_fail_if_invalid_objectType_is_given(self):
        audit_event = self.audit_event_with_db_object()
        audit_event['objectType'] = 'invalid'

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert_equal(res.status_code, 400)
        assert_equal(data['error'], "invalid object type supplied")

    def test_should_fail_if_objectType_but_no_objectId_is_given(self):
        audit_event = self.audit_event_with_db_object()
        del audit_event['objectId']

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert_equal(res.status_code, 400)
        assert_equal(data['error'], "object type cannot be provided without an object ID")

    def test_should_fail_if_objectId_but_no_objectType_is_given(self):
        audit_event = self.audit_event_with_db_object()
        del audit_event['objectType']

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert_equal(res.status_code, 400)
        assert_equal(data['error'], "object ID cannot be provided without an object type")

    def test_should_fail_if_db_object_does_not_exist(self):
        audit_event = self.audit_event_with_db_object()
        audit_event['objectId'] = 6

        res = self.client.post(
            '/audit-events',
            data=json.dumps({'auditEvents': audit_event}),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert_equal(res.status_code, 400)
        assert_equal(data['error'], "referenced object does not exist")
