import pendulum

from flask import json
from nose.tools import (assert_equal,
                        assert_in)

from app.models import (Service,
                        Supplier,
                        Framework,
                        AuditEvent,
                        FrameworkLot,
                        Address)
from app import db
from tests.app.helpers import BaseApplicationTest

from dmapiclient.audit import AuditTypes


class TestGetService(BaseApplicationTest):
    def setup(self):
        super(TestGetService, self).setup()
        now = pendulum.now('UTC')
        with self.app.app_context():
            db.session.add(Framework(
                id=123,
                name="expired",
                slug="expired",
                framework="g-cloud",
                status="expired",
            ))
            db.session.commit()
            db.session.add(FrameworkLot(
                framework_id=123,
                lot_id=1
            ))
            db.session.add(
                Supplier(code=1, name="Supplier 1",
                         addresses=[Address(address_line="{} Dummy Street 1",
                                            suburb="Dummy",
                                            state="ZZZ",
                                            postal_code="0000",
                                            country='Australia')])
            )
            db.session.add(Service(service_id="123-published-456",
                                   supplier_code=1,
                                   updated_at=now,
                                   created_at=now,
                                   status='published',
                                   data={'foo': 'bar'},
                                   lot_id=1,
                                   framework_id=1))
            db.session.add(Service(service_id="123-disabled-456",
                                   supplier_code=1,
                                   updated_at=now,
                                   created_at=now,
                                   status='disabled',
                                   data={'foo': 'bar'},
                                   lot_id=1,
                                   framework_id=1))
            db.session.add(Service(service_id="123-enabled-456",
                                   supplier_code=1,
                                   updated_at=now,
                                   created_at=now,
                                   status='enabled',
                                   data={'foo': 'bar'},
                                   lot_id=1,
                                   framework_id=1))
            db.session.add(Service(service_id="123-expired-456",
                                   supplier_code=1,
                                   updated_at=now,
                                   created_at=now,
                                   status='enabled',
                                   data={'foo': 'bar'},
                                   lot_id=1,
                                   framework_id=123))
            db.session.commit()

    def test_get_non_existent_service(self):
        response = self.client.get('/services/9999999999')

        assert_equal(404, response.status_code)

    def test_invalid_service_id(self):
        response = self.client.get('/services/abc123')

        assert_equal(404, response.status_code)

    def test_get_published_service(self):
        response = self.client.get('/services/123-published-456')
        data = json.loads(response.get_data())

        assert_equal(200, response.status_code)
        assert_equal("123-published-456", data['services']['id'])

    def test_get_disabled_service(self):
        response = self.client.get('/services/123-disabled-456')
        data = json.loads(response.get_data())

        assert_equal(200, response.status_code)
        assert_equal("123-disabled-456", data['services']['id'])

    def test_get_enabled_service(self):
        response = self.client.get('/services/123-enabled-456')
        data = json.loads(response.get_data())

        assert_equal(200, response.status_code)
        assert_equal("123-enabled-456", data['services']['id'])

    def test_get_service_returns_supplier_info(self):
        response = self.client.get('/services/123-published-456')
        data = json.loads(response.get_data())

        assert_equal(data['services']['supplierCode'], 1)
        assert_equal(data['services']['supplierName'], 'Supplier 1')

    def test_get_service_returns_framework_and_lot_info(self):
        response = self.client.get('/services/123-published-456')
        data = json.loads(response.get_data())

        framework_info = {
            key: value for key, value in data['services'].items()
            if key.startswith('framework') or key.startswith('lot')
        }

        assert framework_info == {
            'frameworkSlug': 'g-cloud-6',
            'frameworkName': 'G-Cloud 6',
            'frameworkFramework': 'g-cloud',
            'frameworkStatus': 'live',
            'lot': 'saas',
            'lotSlug': 'saas',
            'lotName': 'Software as a Service',
        }

    def test_get_service_returns_empty_unavailability_audit_if_published(self):
        # create an audit event for the disabled service
        with self.app.app_context():
            service = Service.query.filter(
                Service.service_id == '123-published-456'
            ).first()
            audit_event = AuditEvent(
                audit_type=AuditTypes.update_service_status,
                db_object=service,
                user='joeblogs',
                data={
                    "supplierId": 1,
                    "newArchivedServiceId": 2,
                    "new_status": "published",
                    "supplierName": "Supplier 1",
                    "serviceId": "123-published-456",
                    "old_status": "disabled",
                    "oldArchivedServiceId": 1
                }
            )
            db.session.add(audit_event)
            db.session.commit()
        response = self.client.get('/services/123-disabled-456')
        data = json.loads(response.get_data())

        assert_equal(data['serviceMadeUnavailableAuditEvent'], None)

    def test_get_service_returns_unavailability_audit_if_disabled(self):
        # create an audit event for the disabled service
        with self.app.app_context():
            service = Service.query.filter(
                Service.service_id == '123-disabled-456'
            ).first()
            audit_event = AuditEvent(
                audit_type=AuditTypes.update_service_status,
                db_object=service,
                user='joeblogs',
                data={
                    "supplierId": 1,
                    "newArchivedServiceId": 2,
                    "new_status": "disabled",
                    "supplierName": "Supplier 1",
                    "serviceId": "123-disabled-456",
                    "old_status": "published",
                    "oldArchivedServiceId": 1
                }
            )
            db.session.add(audit_event)
            db.session.commit()
        response = self.client.get('/services/123-disabled-456')
        data = json.loads(response.get_data())

        assert_equal(data['serviceMadeUnavailableAuditEvent']['type'], 'update_service_status')
        assert_equal(data['serviceMadeUnavailableAuditEvent']['user'], 'joeblogs')
        assert_in('createdAt', data['serviceMadeUnavailableAuditEvent'])
        assert_equal(data['serviceMadeUnavailableAuditEvent']['data']['serviceId'], '123-disabled-456')
        assert_equal(data['serviceMadeUnavailableAuditEvent']['data']['old_status'], 'published')
        assert_equal(data['serviceMadeUnavailableAuditEvent']['data']['new_status'], 'disabled')

    def test_get_service_returns_unavailability_audit_if_published_but_framework_is_expired(self):
        # create an audit event for the disabled service
        with self.app.app_context():
            # get expired framework
            framework = Framework.query.filter(
                Framework.id == 123
            ).first()
            # create an audit event for the framework status change
            audit_event = AuditEvent(
                audit_type=AuditTypes.framework_update,
                db_object=framework,
                user='joeblogs',
                data={
                    "update": {
                        "status": "expired",
                        "clarificationQuestionsOpen": "true"
                    }
                }
            )
            # make a published service use the expired framework
            Service.query.filter(
                Service.service_id == '123-published-456'
            ).update({
                'framework_id': 123
            })
            db.session.add(audit_event)
            db.session.commit()
        response = self.client.get('/services/123-published-456')
        data = json.loads(response.get_data())

        assert_equal(data['serviceMadeUnavailableAuditEvent']['type'], 'framework_update')
        assert_equal(data['serviceMadeUnavailableAuditEvent']['user'], 'joeblogs')
        assert_in('createdAt', data['serviceMadeUnavailableAuditEvent'])
        assert_equal(data['serviceMadeUnavailableAuditEvent']['data']['update']['status'], 'expired')

    def test_get_service_returns_correct_unavailability_audit_if_disabled_but_framework_is_expired(self):
        # create an audit event for the disabled service
        with self.app.app_context():
            # get expired framework
            framework = Framework.query.filter(
                Framework.id == 123
            ).first()
            # create an audit event for the framework status change
            audit_event = AuditEvent(
                audit_type=AuditTypes.framework_update,
                db_object=framework,
                user='joeblogs',
                data={
                    "update": {
                        "status": "expired",
                        "clarificationQuestionsOpen": "true"
                    }
                }
            )
            # make a disabled service use the expired framework
            Service.query.filter(
                Service.service_id == '123-disabled-456'
            ).update({
                'framework_id': 123
            })
            db.session.add(audit_event)
            db.session.commit()
        response = self.client.get('/services/123-disabled-456')
        data = json.loads(response.get_data())
        assert_equal(data['serviceMadeUnavailableAuditEvent']['type'], 'framework_update')
        assert_equal(data['serviceMadeUnavailableAuditEvent']['user'], 'joeblogs')
        assert_in('createdAt', data['serviceMadeUnavailableAuditEvent'])
        assert_equal(data['serviceMadeUnavailableAuditEvent']['data']['update']['status'], 'expired')
