import pytest
from tests.bases import BaseApplicationTest, JSONUpdateTestMixin
from datetime import datetime
from flask import json
import mock
from app.models import AuditEvent, Supplier, ContactInformation, Service, Framework, DraftService
from app import db
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from tests.helpers import FixtureMixin, load_example_listing


class DraftsHelpersMixin(BaseApplicationTest, FixtureMixin):
    service_id = None
    updater_json = None
    create_draft_json = None
    basic_questions_json = None

    def setup(self):
        super().setup()

        payload = load_example_listing("G6-SaaS")

        self.service_id = str(payload['id'])
        self.updater_json = {
            'updated_by': 'joeblogs'
        }
        self.create_draft_json = self.updater_json.copy()
        self.create_draft_json['services'] = {
            'frameworkSlug': 'g-cloud-7',
            'lot': 'scs',
            'supplierId': 1
        }
        self.basic_questions_json = {
            'questionsToCopy': ['serviceName']
        }

        db.session.add(
            Supplier(supplier_id=1, name=u"Supplier 1")
        )
        db.session.add(
            Supplier(supplier_id=2, name=u"Supplier 2")
        )
        db.session.add(
            ContactInformation(
                supplier_id=1,
                contact_name=u"Liz",
                email=u"liz@royal.gov.uk",
                postcode=u"SW1A 1AA"
            )
        )
        Framework.query.filter_by(slug='g-cloud-5') \
            .update(dict(status='live'))
        Framework.query.filter_by(slug='g-cloud-7') \
            .update(dict(status='open'))

        self.setup_dummy_service(
            service_id=self.service_id,
            **payload
        )

    def service_count(self):
        return Service.query.count()

    def draft_service_count(self):
        return DraftService.query.count()

    def create_draft_service(self):
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')
        assert res.status_code == 201
        draft = json.loads(res.get_data())['services']

        g7_complete = load_example_listing("G7-SCS").copy()
        g7_complete.pop('id')
        draft_update_json = {'services': g7_complete,
                             'updated_by': 'joeblogs'}
        res2 = self.client.post(
            '/draft-services/{}'.format(draft['id']),
            data=json.dumps(draft_update_json),
            content_type='application/json')
        assert res2.status_code == 200
        draft = json.loads(res2.get_data())['services']

        return draft

    def complete_draft_service(self, draft_id):
        return self.client.post(
            '/draft-services/{}/complete'.format(draft_id),
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

    def publish_draft_service(self, draft_id):
        return self.client.post(
            '/draft-services/{}/publish'.format(draft_id),
            data=json.dumps({
                'updated_by': 'joeblogs'
            }),
            content_type='application/json')

    def publish_new_draft_service(self):
        draft = self.create_draft_service()
        res = self.complete_draft_service(draft['id'])
        assert res.status_code == 200

        res = self.publish_draft_service(draft['id'])
        assert res.status_code == 200

        return res


class TestCopyDraftServiceFromExistingService(DraftsHelpersMixin):
    def test_reject_copy_with_no_updated_by(self):
        res = self.client.put(
            '/draft-services/copy-from/0000000000',
            data=json.dumps({}),
            content_type='application/json',
        )
        assert res.status_code == 400
        assert "'updated_by' is a required property" in json.loads(res.get_data(as_text=True))['error']

    def test_reject_invalid_service_id_on_copy(self):
        res = self.client.put(
            '/draft-services/copy-from/invalid-id!',
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert res.status_code == 400
        assert "Invalid service ID supplied: invalid-id!" in json.loads(res.get_data(as_text=True))['error']

    def test_should_404_if_service_does_not_exist_on_copy(self):
        res = self.client.put(
            '/draft-services/copy-from/0000000000',
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert res.status_code == 404

    @mock.patch('app.db.session.commit')
    def test_copy_from_existing_service_catches_db_integrity_error(self, db_commit):
        db_commit.side_effect = IntegrityError("Could not commit", orig=None, params={})
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert res.status_code == 400
        assert "Could not commit" in json.loads(res.get_data())['error']

    def test_should_create_draft_from_existing_service(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert res.status_code == 201
        assert data['services']['serviceId'] == self.service_id
        assert data['services']['frameworkSlug'] == 'g-cloud-6'

    def test_create_draft_from_existing_should_create_audit_event(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert res.status_code == 201
        draft_id = res.json["services"]["id"]

        res = self.client.get("/audit-events")
        assert res.status_code == 200

        all_audit_events = res.json["auditEvents"]
        assert len(all_audit_events) == 1
        assert all_audit_events[0]["user"] == "joeblogs"
        assert all_audit_events[0]["type"] == "create_draft_service"
        assert all_audit_events[0]["data"]["serviceId"] == self.service_id

        res = self.client.get(f"/audit-events?data-draft-service-id={draft_id}")
        assert res.status_code == 200

        draft_service_audit_events = res.json["auditEvents"]
        assert all_audit_events == draft_service_audit_events

    def test_should_not_create_two_drafts_from_existing_service(self):
        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert res.status_code == 400
        assert 'Draft already exists for service {}'.format(self.service_id) in data['error']

    def test_submission_draft_should_not_prevent_draft_being_created_from_existing_service(self):
        res = self.publish_new_draft_service()

        service = json.loads(res.get_data())['services']

        res = self.client.put(
            '/draft-services/copy-from/{}'.format(service['id']),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert res.status_code == 201

    def test_should_create_draft_on_different_framework_if_passed_target_framework(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps({
                **self.updater_json,
                **self.basic_questions_json,
                'targetFramework': 'g-cloud-7'
            }),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert res.status_code == 201
        assert data['services']['frameworkSlug'] == 'g-cloud-7'
        assert data['services']['copiedFromServiceId'] == self.service_id
        assert 'serviceId' not in data['services']

    def test_should_404_if_target_framework_does_not_exist(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps({
                **self.updater_json,
                **self.basic_questions_json,
                'targetFramework': 'z-cloud'
            }),
            content_type='application/json')

        assert res.status_code == 404

    def test_400_if_target_framework_and_not_questions_to_copy(self):
        res = self.client.put(
            '/draft-services/copy-from/0000000000',
            data=json.dumps({
                **self.updater_json,
                'targetFramework': 'g-cloud-7'
            }),
            content_type='application/json',
        )
        assert res.status_code == 400
        assert "Required data missing: 'questions_to_copy'" in json.loads(res.get_data(as_text=True))['error']

    def test_existing_copied_draft_does_not_prevent_copy_to_new_framework(self):
        res1 = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert res1.status_code == 201

        res2 = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps({
                **self.updater_json,
                **self.basic_questions_json,
                'targetFramework': 'g-cloud-7'
            }),
            content_type='application/json')

        assert res2.status_code == 201

    def test_only_specified_questions_are_copied(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps({
                **self.updater_json,
                'targetFramework': 'g-cloud-7',
                'questionsToCopy': ['serviceBenefits', 'termsAndConditionsDocumentURL']
            }),
            content_type='application/json')
        assert res.status_code == 201

        draft = DraftService.query.filter(
            DraftService.framework_id == 4,
        ).first()

        assert set(draft.data.keys()) == {
            'serviceBenefits',
            'termsAndConditionsDocumentURL',
            'copiedFromServiceId'
        }

    def test_source_service_is_marked_as_copied_after_copy_to_new_framework(self):
        pre_copy_source_service = Service.query.first()
        assert pre_copy_source_service.copied_to_following_framework is False

        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps({
                **self.updater_json,
                **self.basic_questions_json,
                'targetFramework': 'g-cloud-7'
            }),
            content_type='application/json')
        assert res.status_code == 201
        # Source Service ID present in newly created draft
        assert json.loads(res.get_data())['services']['copiedFromServiceId'] == self.service_id

        post_copy_source_service = Service.query.first()
        assert post_copy_source_service.copied_to_following_framework is True

    def test_source_service_is_not_marked_as_copied_if_copied_to_same_framework(self):
        pre_copy_source_service = Service.query.first()
        assert pre_copy_source_service.copied_to_following_framework is False

        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps({
                **self.updater_json,
            }),
            content_type='application/json')
        assert res.status_code == 201
        # Source Service ID not present in newly created draft
        assert json.loads(res.get_data())['services'].get('copiedFromServiceId') is None

        post_copy_source_service = Service.query.first()
        assert post_copy_source_service.copied_to_following_framework is False

    @pytest.mark.parametrize('framework_status', Framework.STATUSES)
    def test_services_can_not_be_copied_to_a_framework_that_is_not_open(self, framework_status):
        if framework_status == 'open':
            return

        self.set_framework_status('g-cloud-7', framework_status)

        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps({
                **self.updater_json,
                **self.basic_questions_json,
                'targetFramework': 'g-cloud-7'
            }),
            content_type='application/json')

        assert res.status_code == 400
        assert 'Target framework is not open' in res.get_data(as_text=True)


class TestCopyPublishedFromFramework(DraftsHelpersMixin):
    def post_to_copy_published_from_framework(
        self, source_framework_slug="g-cloud-6", override_questions_to_copy=None, target_framework_slug='g-cloud-7'
    ):
        """
        :param source_framework_slug: The framework slug for the services being copied.
        :param override_questions_to_copy: A list of questions to copy, rather than the default fixture. There is a
                                           special case where an empty list is used. This causes the 'questionsToCopy'
                                           key to be skipped from the request data, for test purposes.
        :param target_framework_slug: The frameworks slug for where the drafts are being created.
        :return: The json response from the api
        """
        data = {
            **self.updater_json,
            "sourceFrameworkSlug": source_framework_slug,
            "supplierId": 1,
        }

        if override_questions_to_copy == []:
            pass
        elif override_questions_to_copy:
            data.update(questionsToCopy=override_questions_to_copy)
        else:
            data.update(self.basic_questions_json)

        res = self.client.post(
            f'/draft-services/{target_framework_slug}/paas/copy-published-from-framework',
            data=json.dumps(data),
            content_type="application/json",
        )

        return res

    def test_should_copy_all_lots_services_to_new_framwork(self):
        self.setup_dummy_services(5, supplier_id=1, lot_id=2)

        services = Service.query.filter(
            Service.supplier_id == 1,
            Service.framework_id == 1,  # G-Cloud 6
            Service.lot_id == 2,
        ).order_by(
            desc(Service.data['serviceName'].astext)
        ).all()

        res = self.post_to_copy_published_from_framework()
        assert res.status_code == 201

        data = json.loads(res.get_data(as_text=True))
        drafts_count = data['services']['draftsCreatedCount']

        db_drafts = DraftService.query.filter(
            DraftService.supplier_id == 1,
            DraftService.framework_id == 4,  # G-Cloud 7
            DraftService.lot_id == 2,
        ).order_by(DraftService.id).all()

        assert drafts_count == 5
        assert len(db_drafts) == 5
        assert all(draft_service.status == 'not-submitted' for draft_service in db_drafts)
        assert all(draft_service.framework.slug == 'g-cloud-7' for draft_service in db_drafts)
        assert all(draft_service.service_id is None for draft_service in db_drafts)
        for service, db_draft in zip(services, db_drafts):
            assert service.data['serviceName'] == db_draft.data['serviceName']

    def test_should_400_if_no_source_framework_slug(self):
        res = self.post_to_copy_published_from_framework(source_framework_slug=None)

        assert res.status_code == 400
        assert "Required data missing: 'source_framework_slug'" in res.get_data(as_text=True)

    def test_should_400_if_no_questions_to_copy(self):
        res = self.post_to_copy_published_from_framework(override_questions_to_copy=[])

        assert res.status_code == 400
        assert "Required data missing: 'questions_to_copy'" in json.loads(res.get_data(as_text=True))['error']

    def test_should_400_if_questions_to_copy_is_not_a_list(self):
        res = self.post_to_copy_published_from_framework(override_questions_to_copy='Not a list')

        assert res.status_code == 400
        assert "Data error: 'questions_to_copy' must be a list" in json.loads(res.get_data(as_text=True))['error']

    def test_should_404_if_framework_does_not_exist(self):
        res = self.post_to_copy_published_from_framework(target_framework_slug='z-cloud')

        assert res.status_code == 404

    @pytest.mark.parametrize('framework_status', Framework.STATUSES)
    def test_should_400_if_target_framework_not_open(self, framework_status):
        if framework_status == 'open':
            return

        self.set_framework_status('g-cloud-7', framework_status)

        res = self.post_to_copy_published_from_framework()
        assert res.status_code == 400

        assert 'Target framework is not open' in res.get_data(as_text=True)

    def test_should_only_copy_published_services_from_correct_framework_and_lot(self):
        self.setup_dummy_services(3, supplier_id=1, lot_id=1, status='published')
        self.setup_dummy_services(2, supplier_id=1, lot_id=1, status='disabled', start_id=3)
        self.setup_dummy_services(4, supplier_id=1, lot_id=2, status='published', start_id=5)
        self.setup_dummy_services(1, supplier_id=1, lot_id=2, status='disabled', start_id=9)
        self.setup_dummy_services(2, supplier_id=1, lot_id=3, status='published', start_id=10)
        self.setup_dummy_services(3, supplier_id=1, lot_id=3, status='enabled', start_id=12)

        services = Service.query.filter(
            Service.supplier_id == 1,
            Service.framework_id == 1,  # G-Cloud 6
            Service.lot_id == 2,
            Service.status == 'published'
        ).order_by(
            desc(Service.data['serviceName'].astext)
        ).all()

        res = self.post_to_copy_published_from_framework()
        assert res.status_code == 201

        data = json.loads(res.get_data(as_text=True))
        drafts_count = data['services']['draftsCreatedCount']

        db_drafts = DraftService.query.filter(
            DraftService.supplier_id == 1,
        ).order_by(DraftService.id).all()

        assert drafts_count == 4
        assert all(draft.framework.slug == 'g-cloud-7' for draft in db_drafts)
        assert all(draft.lot.slug == 'paas' for draft in db_drafts)
        assert all(draft.status == 'not-submitted' for draft in db_drafts)
        for service, draft in zip(services, db_drafts):
            assert service.data['serviceName'] == draft.data['serviceName']

    def test_should_only_copy_published_services_from_correct_supplier(self):
        self.setup_additional_dummy_suppliers(1, 'A')
        self.setup_dummy_services(3, supplier_id=1, lot_id=2, status='published')
        self.setup_dummy_services(4, supplier_id=1000, lot_id=2, status='published', start_id=3)

        res = self.post_to_copy_published_from_framework()
        assert res.status_code == 201

        data = json.loads(res.get_data(as_text=True))
        drafts_count = data['services']['draftsCreatedCount']

        db_drafts = DraftService.query.all()

        assert drafts_count == 3
        assert len(db_drafts) == 3
        assert all(draft.supplier_id == 1 for draft in db_drafts)

    def test_should_create_drafts_in_reverse_alphabetical_order_by_service_name(self):
        for service_id, char in enumerate('SERVICE'):
            self.setup_dummy_service(
                str(2000000000 + service_id),
                lot_id=2,
                data={'serviceName': f'{char} service'},
            )

        res = self.post_to_copy_published_from_framework()
        assert res.status_code == 201

        db_drafts = DraftService.query.filter(
            DraftService.supplier_id == 1,
        ).order_by(
            DraftService.id
        ).all()

        assert [draft.data['serviceName'] for draft in db_drafts] == \
            ['V service', 'S service', 'R service', 'I service', 'E service', 'E service', 'C service']

    def test_should_only_copy_questions_specified(self):
        service_data = {
            'serviceName': 'My service',
            'serviceBenefits': 'Free tea and cake',
            'provisioningTime': '4 hours',
            'termsAndConditionsDocumentURL': 'example.com',
            'serviceSummary': 'The best one going',
        }
        self.setup_dummy_services(5, supplier_id=1, lot_id=2, data=service_data)

        questions_to_copy = ["provisioningTime", "termsAndConditionsDocumentURL"]
        questions_to_drop = ["serviceName", "serviceBenefits", "serviceSummary"]

        res = self.post_to_copy_published_from_framework(override_questions_to_copy=questions_to_copy)
        assert res.status_code == 201

        db_drafts = DraftService.query.filter(
            DraftService.supplier_id == 1,
        ).all()

        assert all(question in draft.data for draft in db_drafts for question in questions_to_copy)
        assert all(question not in draft.data for draft in db_drafts for question in questions_to_drop)

    def test_should_mark_source_services_as_copied(self):
        self.setup_dummy_services(5, supplier_id=1, lot_id=2)

        pre_copy_services = Service.query.filter(
            Service.supplier_id == 1,
            Service.framework_id == 1,
            Service.lot_id == 2,
        ).all()

        assert len(pre_copy_services) == 5
        assert all(service.copied_to_following_framework is False for service in pre_copy_services)

        res = self.post_to_copy_published_from_framework()
        assert res.status_code == 201

        post_copy_services = Service.query.filter(
            Service.supplier_id == 1,
            Service.framework_id == 1,
            Service.lot_id == 2,
        ).all()

        assert len(post_copy_services) == 5
        assert all(service.copied_to_following_framework is True for service in post_copy_services)

    def test_should_create_an_audit_event_for_each_service_copied(self):
        self.setup_dummy_services(3, supplier_id=1, lot_id=2)

        res = self.post_to_copy_published_from_framework()
        assert res.status_code == 201

        services = Service.query.filter(
            Service.supplier_id == 1,
            Service.lot_id == 2,
        ).order_by(
            desc(Service.data['serviceName'].astext)
        ).all()
        assert len(services) == 3

        audit_events = AuditEvent.query.all()
        assert len(audit_events) == 3

        for audit_event, service in zip(audit_events, services):
            assert audit_event.user == 'joeblogs'
            assert audit_event.type == 'create_draft_service'
            assert audit_event.data['serviceId'] == service.id

    @mock.patch('app.db.session.commit')
    def test_should_catch_integrity_errors(self, db_commit):
        db_commit.side_effect = IntegrityError("Could not commit", orig=None, params={})

        res = self.post_to_copy_published_from_framework()
        assert res.status_code == 400

        assert "Could not commit" in json.loads(res.get_data())['error']

    def test_uses_with_for_update_for_isolation(self):
        filter_mock = mock.Mock()
        filter_mock.with_for_update.return_value = Service.query
        query_patch = mock.patch('app.main.views.drafts.Service.query')
        query = query_patch.start()
        query.filter.return_value = filter_mock

        self.post_to_copy_published_from_framework()

        query_patch.stop()

        filter_mock.with_for_update.assert_called_once_with(of=Service)


class TestDraftServices(DraftsHelpersMixin):
    def test_reject_list_drafts_no_supplier_id(self):
        res = self.client.get('/draft-services')
        assert res.status_code == 400

    def test_reject_list_drafts_invalid_supplier_id(self):
        res = self.client.get('/draft-services?supplier_id=invalid')
        assert res.status_code == 400

    def test_reject_list_drafts_if_no_supplier_for_id(self):
        res = self.client.get('/draft-services?supplier_id=12345667')
        assert res.status_code == 404

    def test_returns_empty_list_if_no_drafts(self):
        res = self.client.get('/draft-services?supplier_id=1')
        assert res.status_code == 200
        drafts = json.loads(res.get_data())
        assert len(drafts['services']) == 0

    def test_returns_drafts_for_supplier(self):
        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        res = self.client.get('/draft-services?supplier_id=1')
        assert res.status_code == 200
        drafts = json.loads(res.get_data())
        assert len(drafts['services']) == 1

    def test_returns_drafts_for_framework_with_drafts(self):
        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        res = self.client.get(
            '/draft-services?supplier_id=1&framework=g-cloud-6'
        )
        assert res.status_code == 200
        drafts = json.loads(res.get_data())
        assert len(drafts['services']) == 1

    def test_does_not_return_drafts_for_framework_with_no_drafts(self):
        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        res = self.client.get(
            '/draft-services?supplier_id=1&framework=g-cloud-7'
        )
        assert res.status_code == 200
        drafts = json.loads(res.get_data())
        assert len(drafts['services']) == 0

    def test_does_not_return_drafts_from_non_existant_framework(self):
        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        res = self.client.get(
            '/draft-services?supplier_id=1&framework=this-is-not-valid'
        )
        assert res.status_code == 404
        assert json.loads(res.get_data(as_text=True))["error"] == "framework 'this-is-not-valid' not found"

    def test_returns_all_drafts_for_supplier_on_single_page(self):

        now = datetime.utcnow()
        service_ids = [
            1234567890123411,
            1234567890123412,
            1234567890123413,
            1234567890123414,
            1234567890123415,
            1234567890123416,
            1234567890123417,
            1234567890123418,
            1234567890123419,
            1234567890123410
        ]

        for service_id in service_ids:
            db.session.add(
                Service(
                    service_id=str(service_id),
                    supplier_id=1,
                    updated_at=now,
                    status='published',
                    created_at=now,
                    data={'foo': 'bar'},
                    lot_id=1,
                    framework_id=1)
            )
        db.session.commit()
        for service_id in service_ids:
            self.client.put(
                '/draft-services/copy-from/{}'.format(service_id),
                data=json.dumps(self.updater_json),
                content_type='application/json')

        res = self.client.get('/draft-services?supplier_id=1')
        assert res.status_code == 200
        drafts = json.loads(res.get_data())
        assert len(drafts['services']) == 10

    def test_reject_update_with_no_updater_details(self):
        res = self.client.post('/draft-services/0000000000')
        assert res.status_code == 400

    def test_reject_create_with_no_updated_by(self):
        res = self.client.post('/draft-services')
        assert res.status_code == 400

    def test_reject_invalid_service_id_on_get(self):
        res = self.client.get('/draft-services?service_id=invalid-id!')
        assert res.status_code == 400

    def test_reject_delete_with_no_updated_by(self):
        res = self.client.delete('/draft-services/0000000000',
                                 data=json.dumps({}),
                                 content_type='application/json')
        assert res.status_code == 400

    def test_reject_publish_with_no_updated_by(self):
        res = self.client.post('/draft-services/0000000000/publish',
                               data=json.dumps({}),
                               content_type='application/json')
        assert res.status_code == 400

    def test_should_create_draft_with_minimal_data(self):
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert res.status_code == 201
        assert data['services']['frameworkSlug'] == 'g-cloud-7'
        assert data['services']['frameworkName'] == 'G-Cloud 7'
        assert data['services']['status'] == 'not-submitted'
        assert data['services']['supplierId'] == 1
        assert data['services']['lot'] == 'scs'

    def test_create_draft_checks_page_questions(self):
        self.create_draft_json['page_questions'] = ['serviceName']
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert res.status_code == 400
        assert data['error'] == {'serviceName': 'answer_required'}

    def test_create_draft_only_checks_valid_page_questions(self):
        self.create_draft_json['page_questions'] = ['tea_and_cakes']
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')
        assert res.status_code == 201

    def test_create_draft_should_create_audit_event(self):
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')
        assert res.status_code == 201
        draft_id = res.json['services']['id']

        res = self.client.get('/audit-events')
        assert res.status_code == 200

        all_audit_events = res.json["auditEvents"]
        assert len(all_audit_events) == 1
        assert all_audit_events[0]['user'] == 'joeblogs'
        assert all_audit_events[0]['type'] == 'create_draft_service'
        assert all_audit_events[0]['data']['draftId'] == draft_id
        assert all_audit_events[0]['data']['draftJson'] == self.create_draft_json['services']

        res = self.client.get(f"/audit-events?data-draft-service-id={draft_id}")
        assert res.status_code == 200

        draft_service_audit_events = res.json["auditEvents"]
        assert all_audit_events == draft_service_audit_events

    @mock.patch('app.db.session.commit')
    def test_create_draft_catches_db_integrity_error(self, db_commit):
        db_commit.side_effect = IntegrityError("Could not commit", orig=None, params={})
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')

        assert res.status_code == 400
        assert "Could not commit" in json.loads(res.get_data())['error']

    def test_should_not_create_draft_with_invalid_data(self):
        invalid_create_json = self.create_draft_json.copy()
        invalid_create_json['services']['supplierId'] = "ShouldBeInt"
        res = self.client.post(
            '/draft-services',
            data=json.dumps(invalid_create_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert res.status_code == 400
        assert "Invalid supplier ID 'ShouldBeInt'" in data['error']

    def test_should_not_create_draft_on_not_open_framework(self):
        draft_json = self.create_draft_json.copy()
        draft_json['services']['frameworkSlug'] = 'g-cloud-5'
        res = self.client.post(
            '/draft-services',
            data=json.dumps(draft_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert res.status_code == 400
        assert "'g-cloud-5' is not open for submissions" in data['error']

    def test_should_not_create_draft_with_invalid_lot(self):
        draft_json = self.create_draft_json.copy()
        draft_json['services']['lot'] = 'newlot'
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert res.status_code == 400
        assert "Incorrect lot 'newlot' for framework 'g-cloud-7'" in data['error']

    def test_can_save_additional_fields_to_draft(self):
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')
        data = json.loads(res.get_data())
        draft_id = data['services']['id']
        draft_update_json = self.updater_json.copy()
        draft_update_json['services'] = {
            'serviceTypes': ['Implementation'],
            'serviceBenefits': ['Tests pass']
        }

        res2 = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(draft_update_json),
            content_type='application/json')
        data2 = json.loads(res2.get_data())
        assert res2.status_code == 200
        assert data2['services']['frameworkSlug'] == 'g-cloud-7'
        assert data2['services']['frameworkName'] == 'G-Cloud 7'
        assert data2['services']['status'] == 'not-submitted'
        assert data2['services']['supplierId'] == 1
        assert data2['services']['serviceTypes'] == ['Implementation']
        assert data2['services']['serviceBenefits'] == ['Tests pass']

    def test_update_draft_uses_with_for_update_for_isolation(self):
        filter_mock = mock.Mock()
        filter_mock.with_for_update.return_value = DraftService.query
        query_patch = mock.patch('app.main.views.drafts.DraftService.query')
        query = query_patch.start()
        query.filter.return_value = filter_mock

        self.client.post(
            '/draft-services/1234',
            data=json.dumps({
                'services': {
                    'serviceTypes': [
                        'Implementation'
                    ]
                },
                'updated_by': 'Test',
            }),
            content_type='application/json')

        query_patch.stop()

        filter_mock.with_for_update.assert_called_once_with(of=DraftService)

    def test_update_draft_should_create_audit_event(self):
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json',
        )
        draft_id = res.json['services']['id']
        draft_update_json = self.updater_json.copy()
        draft_update_json['services'] = {
            'serviceTypes': ['Implementation'],
            'serviceBenefits': ['Tests pass']
        }

        res = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(draft_update_json),
            content_type='application/json'
        )
        assert res.status_code == 200

        res = self.client.get('/audit-events')
        assert res.status_code == 200

        all_audit_events = res.json["auditEvents"]
        assert len(all_audit_events) == 2
        assert all_audit_events[0]['user'] == 'joeblogs'
        assert all_audit_events[0]['type'] == 'create_draft_service'
        assert all_audit_events[0]['data']['draftId'] == draft_id
        assert all_audit_events[1]['user'] == 'joeblogs'
        assert all_audit_events[1]['type'] == 'update_draft_service'
        assert all_audit_events[1]['data']['draftId'] == draft_id

        res = self.client.get(f"/audit-events?data-draft-service-id={draft_id}")
        assert res.status_code == 200

        draft_service_audit_events = res.json["auditEvents"]
        assert all_audit_events == draft_service_audit_events

    def test_update_draft_should_purge_keys_with_null_values(self):
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')
        data = json.loads(res.get_data())
        draft_id = data['services']['id']

        draft_update_json = self.updater_json.copy()
        draft_update_json['services'] = {
            'serviceName': "What a great service",
            'serviceTypes': ['Implementation'],
            'serviceBenefits': ['Tests pass']
        }
        res2 = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(draft_update_json),
            content_type='application/json')
        assert res2.status_code == 200
        data2 = json.loads(res2.get_data())['services']
        assert('serviceName' in data2)
        assert('serviceBenefits' in data2)
        assert('serviceTypes' in data2)

        draft_update_json['services'] = {
            'serviceTypes': None,
            'serviceBenefits': None
        }
        res3 = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(draft_update_json),
            content_type='application/json')
        assert res3.status_code == 200
        data3 = json.loads(res3.get_data())['services']
        assert('serviceName' in data3)
        assert('serviceBenefits' not in data3)
        assert('serviceTypes' not in data3)

    def test_update_draft_should_validate_full_draft_if_submitted(self):
        draft_id = self.create_draft_service()['id']
        self.complete_draft_service(draft_id)

        res = self.client.get('/draft-services/{}'.format(draft_id))
        submitted_draft = json.loads(res.get_data())['services']
        submitted_draft['serviceName'] = None
        submitted_draft['serviceBenefits'] = None

        draft_update_json = self.updater_json.copy()
        draft_update_json['services'] = submitted_draft

        res2 = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(draft_update_json),
            content_type='application/json')
        errors = json.loads(res2.get_data())['error']

        assert res2.status_code == 400
        assert errors == {u'serviceName': u'answer_required', u'serviceBenefits': u'answer_required'}

    def test_update_draft_should_not_validate_full_draft_if_not_submitted(self):
        draft_id = self.create_draft_service()['id']

        res = self.client.get('/draft-services/{}'.format(draft_id))
        submitted_draft = json.loads(res.get_data())['services']
        submitted_draft['serviceName'] = None
        submitted_draft['serviceBenefits'] = None

        draft_update_json = self.updater_json.copy()
        draft_update_json['services'] = submitted_draft

        res2 = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(draft_update_json),
            content_type='application/json')
        updated_draft = json.loads(res2.get_data())['services']

        assert res2.status_code == 200
        assert updated_draft['status'] == 'not-submitted'
        assert 'serviceName' not in updated_draft
        assert 'serviceBenefits' not in updated_draft

    def test_update_draft_should_ignore_copiedfromserviceid_field(self):
        draft_id = self.create_draft_service()['id']

        res = self.client.get('/draft-services/{}'.format(draft_id))
        submitted_draft = json.loads(res.get_data())['services']
        submitted_draft['copiedFromServiceId'] = "123456789"

        draft_update_json = self.updater_json.copy()
        draft_update_json['services'] = submitted_draft

        res2 = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(draft_update_json),
            content_type='application/json')
        updated_draft = json.loads(res2.get_data())['services']

        assert res2.status_code == 200
        assert 'copiedFromServiceId' in updated_draft

    def test_update_draft_catches_db_integrity_error(self):
        draft_id = self.create_draft_service()['id']
        draft_update_json = self.updater_json.copy()
        draft_update_json['services'] = {
            'serviceTypes': ['Implementation'],
            'serviceBenefits': ['Tests pass']
        }
        with mock.patch('app.db.session.commit') as db_commit:
            db_commit.side_effect = IntegrityError("Could not commit", orig=None, params={})
            res = self.client.post(
                '/draft-services/{}'.format(draft_id),
                data=json.dumps(draft_update_json),
                content_type='application/json')

            assert res.status_code == 400
            assert "Could not commit" in json.loads(res.get_data())['error']

    def test_validation_errors_returned_for_invalid_update_of_new_draft(self):
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')
        data = json.loads(res.get_data())
        draft_id = data['services']['id']
        draft_update_json = self.updater_json.copy()
        draft_update_json['services'] = {
            'serviceTypes': ['Bad Type'],
            'serviceBenefits': ['Too many words 4 5 6 7 8 9 10 11']
        }

        res2 = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(draft_update_json),
            content_type='application/json')
        data2 = json.loads(res2.get_data())
        assert res2.status_code == 400
        assert "'Bad Type' is not one of" in data2['error']['serviceTypes']

    def test_validation_errors_returned_for_invalid_update_of_copy(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        draft_id = json.loads(res.get_data())['services']['id']
        res = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps({
                'updated_by': 'joeblogs',
                'services': {
                    'badField': 'new service name',
                    'priceUnit': 'chickens'
                }
            }),
            content_type='application/json')
        data = json.loads(res.get_data())
        assert res.status_code == 400
        assert "'badField' was unexpected" in str(data['error']['_form'])
        assert "no_unit_specified" in data['error']['priceUnit']

    def test_should_fetch_a_draft(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert res.status_code == 201
        draft_id = json.loads(res.get_data())['services']['id']
        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        assert fetch.status_code == 200
        data = json.loads(res.get_data())
        assert data['services']['serviceId'] == self.service_id

    def test_invalid_draft_should_have_validation_errors(self):
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')
        assert res.status_code == 201

        data = json.loads(res.get_data())

        res = self.client.get('/draft-services/{}'.format(data['services']['id']))
        assert res.status_code == 200
        data = json.loads(res.get_data())
        assert data['validationErrors']

    def test_valid_draft_should_have_no_validation_errors(self):
        draft = self.create_draft_service()

        res = self.client.get('/draft-services/{}'.format(draft['id']))
        assert res.status_code == 200
        data = json.loads(res.get_data())
        assert not data['validationErrors']
        assert data['auditEvents'] is not None

    def test_get_draft_with_no_audit_history(self):
        draft = self.create_draft_service()

        AuditEvent.query.delete()
        db.session.commit()

        res = self.client.get('/draft-services/{}'.format(draft['id']))
        assert res.status_code == 200
        data = json.loads(res.get_data())
        assert data['auditEvents'] is None

    def test_should_404_on_fetch_a_draft_that_doesnt_exist(self):
        fetch = self.client.get('/draft-services/0000000000')
        assert fetch.status_code == 404

    def test_should_404_on_delete_a_draft_that_doesnt_exist(self):
        res = self.client.delete(
            '/draft-services/0000000000',
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert res.status_code == 404

    def test_should_delete_a_draft_copied_from_same_framework(self):
        # Create a new draft by copying from the same framework
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert res.status_code == 201
        draft_id = json.loads(res.get_data())['services']['id']
        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        assert fetch.status_code == 200

        # Delete the draft
        delete = self.client.delete(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert delete.status_code == 200

        # Check the audit events
        res = self.client.get('/audit-events')
        assert res.status_code == 200

        all_audit_events = res.json['auditEvents']
        assert len(all_audit_events) == 2
        assert all_audit_events[0]['type'] == 'create_draft_service'
        assert all_audit_events[1]['user'] == 'joeblogs'
        assert all_audit_events[1]['type'] == 'delete_draft_service'
        assert all_audit_events[1]['data']['serviceId'] == self.service_id

        res = self.client.get(f"/audit-events?data-draft-service-id={draft_id}")
        assert res.status_code == 200

        draft_service_audit_events = res.json["auditEvents"]
        assert all_audit_events == draft_service_audit_events

        # Check the draft has gone
        fetch_again = self.client.get('/draft-services/{}'.format(draft_id))
        assert fetch_again.status_code == 404

    def test_should_delete_a_draft_copied_from_a_different_framework(self):
        # Create a new draft by copying from the same framework
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps({
                **self.updater_json,
                **self.basic_questions_json,
                'targetFramework': 'g-cloud-7'
            }),
            content_type='application/json')
        assert res.status_code == 201
        draft_id = json.loads(res.get_data())['services']['id']

        # Check that the source service ID is there
        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        assert fetch.status_code == 200
        assert json.loads(fetch.get_data())['services']['copiedFromServiceId'] == self.service_id

        # Check that the flag has been set on the source service
        source_service = self.client.get('/services/{}'.format(self.service_id))
        assert json.loads(source_service.get_data())['services']['copiedToFollowingFramework'] is True

        # Reset audit events - we're only interested in the post-delete audits
        AuditEvent.query.delete()
        db.session.commit()

        # Delete the draft
        delete = self.client.delete(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert delete.status_code == 200

        # Check the audit events
        res = self.client.get('/audit-events')
        assert res.status_code == 200

        all_audit_events = res.json['auditEvents']
        assert len(all_audit_events) == 2
        assert all_audit_events[0]['type'] == 'delete_draft_service'
        assert all_audit_events[1]['type'] == 'update_service'
        assert all_audit_events[1]['acknowledged'] is True
        assert all_audit_events[1]['data']['copiedToFollowingFramework'] is False
        assert all_audit_events[1]['data']['supplierName'] == 'Supplier 1'

        res = self.client.get(f"/audit-events?data-draft-service-id={draft_id}")
        assert res.status_code == 200

        draft_service_audit_events = res.json["auditEvents"]
        assert draft_service_audit_events == all_audit_events[0:1]

        # Check the draft has gone
        fetch_again = self.client.get('/draft-services/{}'.format(draft_id))
        assert fetch_again.status_code == 404

        # Check that the source service's flag has been reset
        source_service = self.client.get('/services/{}'.format(self.service_id))
        assert json.loads(source_service.get_data())['services']['copiedToFollowingFramework'] is False

    def test_delete_catches_db_integrity_error(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        draft_id = json.loads(res.get_data())['services']['id']
        with mock.patch('app.db.session.commit') as db_commit:
            db_commit.side_effect = IntegrityError("Could not commit", orig=None, params={})
            res = self.client.delete(
                '/draft-services/{}'.format(draft_id),
                data=json.dumps(self.updater_json),
                content_type='application/json')

            assert res.status_code == 400
            assert "Could not commit" in json.loads(res.get_data())['error']

    def test_should_be_able_to_update_a_draft(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        draft_id = json.loads(res.get_data())['services']['id']
        update = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps({
                'updated_by': 'joeblogs',
                'services': {
                    'serviceName': 'new service name'
                }
            }),
            content_type='application/json')

        data = json.loads(update.get_data())
        assert update.status_code == 200
        assert data['services']['serviceName'] == 'new service name'

        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        data = json.loads(fetch.get_data())
        assert fetch.status_code == 200
        assert data['services']['serviceName'] == 'new service name'

    def test_whitespace_is_stripped_when_updating_a_draft(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        draft_id = json.loads(res.get_data())['services']['id']
        update = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps({
                'updated_by': 'joeblogs',
                'services': {
                    'serviceName': '      a new  service name      ',
                    'serviceFeatures': [
                        "     Feature   1    ",
                        "   ",
                        "",
                        "    second feature    "
                    ],
                }
            }),
            content_type='application/json')

        data = json.loads(update.get_data())
        assert update.status_code == 200
        assert data['services']['serviceName'] == 'a new  service name'

        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        data = json.loads(fetch.get_data())
        assert fetch.status_code == 200
        assert data['services']['serviceName'] == 'a new  service name'
        assert len(data['services']['serviceFeatures']) == 2
        assert data['services']['serviceFeatures'][0] == 'Feature   1'
        assert data['services']['serviceFeatures'][1] == 'second feature'

    def test_should_edit_draft_with_audit_event(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        draft_id = res.json['services']['id']
        update = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps({
                'updated_by': 'joeblogs',
                'services': {
                    'serviceName': 'new service name'
                }
            }),
            content_type='application/json')
        assert update.status_code == 200

        res = self.client.get('/audit-events')
        assert res.status_code == 200

        all_audit_events = res.json['auditEvents']
        assert len(all_audit_events) == 2
        assert all_audit_events[1]['user'] == 'joeblogs'
        assert all_audit_events[1]['type'] == 'update_draft_service'
        assert all_audit_events[1]['data']['serviceId'] == self.service_id
        assert all_audit_events[1]['data']['updateJson']['serviceName'] == 'new service name'

        res = self.client.get(f"/audit-events?data-draft-service-id={draft_id}")
        assert res.status_code == 200

        draft_service_audit_events = res.json["auditEvents"]
        assert all_audit_events == draft_service_audit_events

    def test_should_be_a_400_if_no_service_block_in_update(self):
        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        update = self.client.post(
            '/draft-services/{}'.format(self.service_id),
            data=json.dumps({
                'updated_by': 'joeblogs'
            }),
            content_type='application/json')

        assert update.status_code == 400

    def test_should_not_be_able_to_publish_if_no_draft_exists(self):
        res = self.client.post(
            '/draft-services/98765/publish',
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')
        assert res.status_code == 404

    @mock.patch('app.main.views.drafts.index_service')
    def test_should_be_able_to_publish_valid_copied_draft_service(self, index_service):
        """
        this test creates a draft from a (live) service, updates the draft, and then publishes it.
        publishing the draft updates the original service -- it doesn't create a new one
        this was an alternative editing model proposed by martyn way way back.
        we're not actually doing this anywhere, but it's tested and it looks like it works.
        """
        initial = self.client.get('/services/{}'.format(self.service_id))
        assert initial.status_code == 200
        assert json.loads(initial.get_data())['services']['serviceName'] == 'A SaaS with lots of options'

        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        draft_id = json.loads(res.get_data())['services']['id']
        first_draft = self.client.get(
            '/draft-services/{}'.format(draft_id))
        assert first_draft.status_code == 200
        assert json.loads(first_draft.get_data())['services']['serviceName'] == 'A SaaS with lots of options'

        self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps({
                'updated_by': 'joeblogs',
                'services': {
                    'serviceName': 'chickens'
                }
            }),
            content_type='application/json')

        updated_draft = self.client.get(
            '/draft-services/{}'.format(draft_id))
        assert updated_draft.status_code == 200
        assert json.loads(updated_draft.get_data())['services']['serviceName'] == 'chickens'

        res = self.client.post(
            '/draft-services/{}/publish'.format(draft_id),
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')
        assert res.status_code == 200

        res = self.client.get('/audit-events')
        assert res.status_code == 200

        all_audit_events = res.json['auditEvents']
        assert len(all_audit_events) == 3
        assert all_audit_events[0]['type'] == 'create_draft_service'
        assert all_audit_events[1]['type'] == 'update_draft_service'
        assert all_audit_events[2]['type'] == 'publish_draft_service'

        res = self.client.get(f"/audit-events?data-draft-service-id={draft_id}")
        assert res.status_code == 200

        draft_service_audit_events = res.json["auditEvents"]
        assert all_audit_events == draft_service_audit_events

        # draft should no longer exist
        fetch = self.client.get('/draft-services/{}'.format(self.service_id))
        assert fetch.status_code == 404

        # published should be updated
        updated_draft = self.client.get('/services/{}'.format(self.service_id))
        assert updated_draft.status_code == 200
        assert json.loads(updated_draft.get_data())['services']['serviceName'] == 'chickens'

        # archive should be updated
        archives = self.client.get(
            '/archived-services?service-id={}'.format(self.service_id))
        assert archives.status_code == 200
        assert json.loads(archives.get_data())['services'][0]['serviceName'] == 'chickens'
        assert index_service.called

    def test_should_not_be_able_to_publish_submission_if_not_submitted(self):
        draft = self.create_draft_service()

        res = self.publish_draft_service(draft['id'])
        assert res.status_code == 400

    def test_should_not_be_able_to_republish_submission(self):
        draft = self.create_draft_service()
        self.complete_draft_service(draft['id'])

        res = self.publish_draft_service(draft['id'])
        assert res.status_code == 200

        res = self.publish_draft_service(draft['id'])
        assert res.status_code == 400

    @mock.patch('app.main.views.drafts.index_service')
    def test_search_api_should_be_called_on_publish_if_framework_is_live(self, index_service):
        draft_id = self.create_draft_service()['id']
        self.complete_draft_service(draft_id)

        Framework.query.filter_by(slug='g-cloud-7').update(dict(status='live'))
        db.session.commit()

        res = self.publish_draft_service(draft_id)

        assert res.status_code == 200
        assert index_service.called

    @mock.patch('app.service_utils.search_api_client')
    def test_should_be_able_to_publish_valid_new_draft_service(self, search_api_client):
        draft_id = self.create_draft_service()['id']
        self.complete_draft_service(draft_id)

        res = self.publish_draft_service(draft_id)

        assert res.status_code == 200
        created_service_data = json.loads(res.get_data())
        new_service_id = created_service_data['services']['id']

        res = self.client.get('/audit-events')
        assert res.status_code == 200

        all_audit_events = res.json['auditEvents']
        assert len(all_audit_events) == 4
        assert all_audit_events[0]['type'] == 'create_draft_service'
        assert all_audit_events[1]['type'] == 'update_draft_service'
        assert all_audit_events[2]['type'] == 'complete_draft_service'
        assert all_audit_events[3]['type'] == 'publish_draft_service'

        res = self.client.get(f"/audit-events?data-draft-service-id={draft_id}")
        assert res.status_code == 200

        draft_service_audit_events = res.json["auditEvents"]
        assert all_audit_events == draft_service_audit_events

        # draft should still exist
        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        assert fetch.status_code == 200

        # G-Cloud 7 service should be visible from API
        # (frontends hide them based on statuses)
        fetch2 = self.client.get('/services/{}'.format(new_service_id))
        assert fetch2.status_code == 200
        assert json.loads(fetch2.get_data())['services']['status'] == "published"

        # archive should be updated
        archives = self.client.get(
            '/archived-services?service-id={}'.format(new_service_id))
        assert archives.status_code == 200
        assert json.loads(archives.get_data())['services'][0]['serviceName'] == 'An example G-7 SCS Service'

        # service should not be indexed as G-Cloud 7 is not live
        assert not search_api_client.index.called

    def test_submitted_drafts_are_not_deleted_when_published(self):
        draft = self.create_draft_service()
        self.complete_draft_service(draft['id'])

        assert self.draft_service_count() == 1
        assert self.publish_draft_service(draft['id']).status_code == 200
        assert self.draft_service_count() == 1

    @mock.patch('app.main.views.drafts.index_service')
    def test_drafts_made_from_services_are_deleted_when_published(self, index_service):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        draft = json.loads(res.get_data())['services']

        assert self.service_count() == 1
        assert self.draft_service_count() == 1

        assert self.publish_draft_service(draft['id']).status_code == 200

        assert self.service_count() == 1
        assert self.draft_service_count() == 0

    @mock.patch('app.models.main.random_positive_external_id')
    def test_service_id_collisions_should_be_handled(self, random_positive_external_id):
        # Return the same ID a few times (cause collisions) and then return a different one.
        random_positive_external_id.side_effect = (
            '123456789012345',
            '123456789012345',
            '123456789012345',
            '222222222222222',
        )

        res = self.publish_new_draft_service()
        assert res.status_code == 200
        res = self.publish_new_draft_service()
        assert res.status_code == 200

        # Count is 3 because we create one in the setup
        assert self.service_count() == 3
        res = self.client.get('/services?framework=g-cloud-7')
        services = json.loads(res.get_data())['services']
        assert services[0]['id'] == '123456789012345'
        assert services[1]['id'] == '222222222222222'
        assert self.draft_service_count() == 2

    def test_get_draft_returns_last_audit_event(self):
        draft = json.loads(self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json'
        ).get_data())['services']

        res = self.client.get(
            '/draft-services/{}'.format(draft['id']),
            data=json.dumps(self.create_draft_json),
            content_type='application/json'
        )

        assert res.status_code == 200
        data = json.loads(res.get_data())
        draft, audit_event = data['services'], data['auditEvents']

        assert audit_event['type'] == 'create_draft_service'


class TestListDraftServiceByFramework(DraftsHelpersMixin):

    def test_list_drafts_for_framework_paginates_results(self):
        for i in range(1, 11):
            self.create_draft_service()

        res = self.client.get('/draft-services/framework/g-cloud-7')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        # Assert that IDs are in ascending order
        draft_ids = [draft['id'] for draft in data['services']]
        assert all(x <= y for x, y in zip(draft_ids, draft_ids[1:]))

        assert len(data['services']) == 5
        assert data['meta']['total'] == 10
        assert data['links']['next'] == 'http://127.0.0.1:5000/draft-services/framework/g-cloud-7?page=2'
        assert data['links']['last'] == 'http://127.0.0.1:5000/draft-services/framework/g-cloud-7?page=2'
        assert data['links']['self'] == 'http://127.0.0.1:5000/draft-services/framework/g-cloud-7'

    def test_list_drafts_for_framework_page2(self):
        for i in range(1, 11):
            self.create_draft_service()

        res = self.client.get('/draft-services/framework/g-cloud-7?page=2')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        # Assert that IDs are in ascending order
        draft_ids = [draft['id'] for draft in data['services']]
        assert all(x <= y for x, y in zip(draft_ids, draft_ids[1:]))

        assert len(data['services']) == 5
        assert data['meta']['total'] == 10
        assert data['links']['prev'] == 'http://127.0.0.1:5000/draft-services/framework/g-cloud-7?page=1'
        assert data['links']['self'] == 'http://127.0.0.1:5000/draft-services/framework/g-cloud-7?page=2'

    @pytest.mark.parametrize('status, expected_count', [
        ('not-submitted', 4),
        ('submitted', 1)
    ])
    def test_list_drafts_filters_by_status(self, status, expected_count):
        for i in range(1, 6):
            self.create_draft_service()
        # Mark a draft as submitted
        self.complete_draft_service(DraftService.query.first().id)

        res = self.client.get(f'/draft-services/framework/g-cloud-7?status={status}')
        data = json.loads(res.get_data(as_text=True))

        assert data['meta']['total'] == expected_count
        for draft in data['services']:
            assert draft['status'] == status

    def test_list_drafts_filters_by_supplier_id(self):
        draft1 = self.create_draft_service()
        # Use the JSON from draft 1 to create draft 2, with a different supplier ID
        draft1['supplierId'] = 2
        draft_update_json = {'services': draft1,
                             'updated_by': 'joeblogs'}

        self.client.post(
            '/draft-services',
            data=json.dumps(draft_update_json),
            content_type='application/json'
        )

        res = self.client.get(f'/draft-services/framework/g-cloud-7?supplier_id=2')
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))

        assert data['meta']['total'] == 1
        assert data['services'][0]['supplierId'] == 2

    def test_list_drafts_page_out_of_range_returns_404(self):
        for i in range(1, 11):
            self.create_draft_service()

        res = self.client.get('/draft-services/framework/g-cloud-7?page=3')

        assert res.status_code == 404

    def test_list_drafts_requires_valid_status(self):
        res = self.client.get(f'/draft-services/framework/g-cloud-7?status=kraftwerk')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == "Invalid argument: status must be 'submitted' or 'not-submitted'"

    def test_list_drafts_requires_valid_framework(self):
        res = self.client.get(f'/draft-services/framework/x-cloud-99')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 404
        assert data['error'] == "Framework 'x-cloud-99' not found"

    def test_list_drafts_requires_valid_supplier_id(self):
        res = self.client.get(f'/draft-services/framework/g-cloud-7?supplier_id=the-human-league')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == "Invalid supplier_id: the-human-league"

    def test_list_drafts_requires_supplier_id_to_exist(self):
        res = self.client.get(f'/draft-services/framework/g-cloud-7?supplier_id=999')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 404
        assert data['error'] == "Supplier_id '999' not found"


class TestCopyDraft(BaseApplicationTest, JSONUpdateTestMixin):
    endpoint = '/draft-services/{self.draft_id}/copy'
    method = 'post'

    def setup(self):
        super(TestCopyDraft, self).setup()

        db.session.add(
            Supplier(supplier_id=1, name=u"Supplier 1")
        )
        db.session.add(
            ContactInformation(
                supplier_id=1,
                contact_name=u"Liz",
                email=u"liz@royal.gov.uk",
                postcode=u"SW1A 1AA"
            )
        )
        Framework.query.filter_by(slug='g-cloud-5') \
            .update(dict(status='live'))
        Framework.query.filter_by(slug='g-cloud-7') \
            .update(dict(status='open'))
        db.session.commit()

        create_draft_json = {
            'updated_by': 'joeblogs',
            'services': {
                'frameworkSlug': 'g-cloud-7',
                'lot': 'scs',
                'supplierId': 1,
                'serviceName': "Draft",
                'status': 'submitted',
                'serviceSummary': 'This is a summary',
                "termsAndConditionsDocumentURL": "http://localhost/example.pdf",
                "pricingDocumentURL": "http://localhost/example.pdf",
                "serviceDefinitionDocumentURL": "http://localhost/example.pdf",
                "sfiaRateDocumentURL": "http://localhost/example.pdf",
            }
        }

        draft = self.client.post(
            '/draft-services',
            data=json.dumps(create_draft_json),
            content_type='application/json')

        self.draft = json.loads(draft.get_data())['services']
        self.draft_id = self.draft['id']

    def test_copy_draft(self):
        res = self.client.post(
            '/draft-services/{}/copy'.format(self.draft_id),
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert res.status_code == 201, res.get_data()
        assert data['services']['lot'] == 'scs'
        assert data['services']['status'] == 'not-submitted'
        assert data['services']['serviceName'] == 'Draft copy'
        assert data['services']['supplierId'] == 1
        assert data['services']['frameworkSlug'] == self.draft['frameworkSlug']
        assert data['services']['frameworkName'] == self.draft['frameworkName']

    def test_copy_draft_should_create_audit_event(self):
        res = self.client.post(
            '/draft-services/{}/copy'.format(self.draft_id),
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert res.status_code == 201
        data = json.loads(res.get_data())
        draft_id = data['services']['id']

        res = self.client.get('/audit-events')
        assert res.status_code == 200

        all_audit_events = res.json["auditEvents"]
        assert len(all_audit_events) == 2
        assert all_audit_events[1]['user'] == 'joeblogs'
        assert all_audit_events[1]['type'] == 'create_draft_service'
        assert all_audit_events[1]['data'] == {
            'draftId': draft_id,
            'originalDraftId': self.draft_id,
            'supplierId': 1,
        }

        res = self.client.get(f"/audit-events?data-draft-service-id={draft_id}")
        assert res.status_code == 200

        draft_service_audit_events = res.json["auditEvents"]
        assert all_audit_events[1:2] == draft_service_audit_events

    def test_should_not_create_draft_with_invalid_data(self):
        res = self.client.post(
            '/draft-services/1000/copy',
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert res.status_code == 404

    def test_should_not_copy_draft_service_description(self):
        res = self.client.post(
            '/draft-services/{}/copy'.format(self.draft_id),
            data=json.dumps({"updated_by": "me"}),
            content_type="application/json")
        data = json.loads(res.get_data())

        assert res.status_code == 201
        assert "serviceSummary" not in data['services']

    def test_should_not_copy_draft_documents(self):
        res = self.client.post(
            '/draft-services/{}/copy'.format(self.draft_id),
            data=json.dumps({"updated_by": "me"}),
            content_type="application/json")
        data = json.loads(res.get_data())

        assert res.status_code == 201
        assert "termsAndConditionsDocumentURL" not in data['services']
        assert "pricingDocumentURL" not in data['services']
        assert "serviceDefinitionDocumentURL" not in data['services']
        assert "sfiaRateDocumentURL" not in data['services']

    @mock.patch('app.db.session.commit')
    def test_copy_draft_service_should_catch_db_integrity_error(self, db_commit):
        db_commit.side_effect = IntegrityError("Could not commit", orig=None, params={})
        res = self.client.post(
            '/draft-services/{}/copy'.format(self.draft_id),
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert res.status_code == 400
        assert "Could not commit" in json.loads(res.get_data())['error']


class TestCompleteDraft(BaseApplicationTest, JSONUpdateTestMixin):
    endpoint = '/draft-services/{self.draft_id}/complete'
    method = 'post'

    def setup(self):
        super(TestCompleteDraft, self).setup()

        db.session.add(Supplier(supplier_id=1, name=u"Supplier 1"))
        db.session.add(
            ContactInformation(
                supplier_id=1,
                contact_name=u"Test",
                email=u"supplier@user.dmdev",
                postcode=u"SW1A 1AA"
            )
        )
        Framework.query.filter_by(slug='g-cloud-7').update(dict(status='open'))
        db.session.commit()
        draft_json = load_example_listing("G7-SCS")
        draft_json['frameworkSlug'] = 'g-cloud-7'
        create_draft_json = {
            'updated_by': 'joeblogs',
            'services': draft_json
        }

        draft = self.client.post(
            '/draft-services',
            data=json.dumps(create_draft_json),
            content_type='application/json')

        self.draft = json.loads(draft.get_data())['services']
        self.draft_id = self.draft['id']

    def test_complete_draft(self):
        res = self.client.post(
            '/draft-services/{}/complete'.format(self.draft_id),
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert res.status_code == 200, res.get_data()
        assert data['services']['status'] == 'submitted'

    def test_complete_draft_should_create_audit_event(self):
        res = self.client.post(
            '/draft-services/{}/complete'.format(self.draft_id),
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json',
        )
        assert res.status_code == 200
        draft_id = res.json["services"]["id"]

        res = self.client.get('/audit-events')
        assert res.status_code == 200

        all_audit_events = res.json['auditEvents']
        assert len(all_audit_events) == 2
        assert all_audit_events[1]['user'] == 'joeblogs'
        assert all_audit_events[1]['type'] == 'complete_draft_service'
        assert all_audit_events[1]['data'] == {
            'draftId': self.draft_id,
            'supplierId': 1,
        }

        res = self.client.get(f"/audit-events?data-draft-service-id={draft_id}")
        assert res.status_code == 200

        draft_service_audit_events = res.json["auditEvents"]
        assert all_audit_events == draft_service_audit_events

    def test_should_not_complete_draft_without_updated_by(self):
        res = self.client.post(
            '/draft-services/{}/complete'.format(self.draft_id),
            data=json.dumps({}),
            content_type='application/json')

        assert res.status_code == 400

    def test_should_not_complete_invalid_draft(self):
        create_draft_json = {
            'updated_by': 'joeblogs',
            'services': {
                'frameworkSlug': 'g-cloud-7',
                'lot': 'scs',
                'supplierId': 1,
                'serviceName': 'Name',
            }
        }

        draft = self.client.post(
            '/draft-services',
            data=json.dumps(create_draft_json),
            content_type='application/json'
        )

        draft = json.loads(draft.get_data())['services']

        res = self.client.post(
            '/draft-services/{}/complete'.format(draft['id']),
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert res.status_code == 400
        errors = json.loads(res.get_data())['error']
        assert 'serviceSummary' in errors

    @mock.patch('app.db.session.commit')
    def test_complete_draft_catches_db_integrity_errors(self, db_commit):
        db_commit.side_effect = IntegrityError("Could not commit", orig=None, params={})
        res = self.client.post(
            '/draft-services/{}/complete'.format(self.draft_id),
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert res.status_code == 400
        assert "Could not commit" in json.loads(res.get_data())['error']


class TestDOSServices(BaseApplicationTest, FixtureMixin):
    updater_json = None
    create_draft_json = None

    def setup(self):
        super(TestDOSServices, self).setup()

        payload = load_example_listing("DOS-digital-specialist")
        self.updater_json = {
            'updated_by': 'joeblogs'
        }
        self.create_draft_json = self.updater_json.copy()
        self.create_draft_json['services'] = payload
        self.create_draft_json['services']['frameworkSlug'] = 'digital-outcomes-and-specialists'

        self.set_framework_status('digital-outcomes-and-specialists', 'open')

        db.session.add(
            Supplier(supplier_id=1, name=u"Supplier 1")
        )
        db.session.add(
            ContactInformation(
                supplier_id=1,
                contact_name=u"Liz",
                email=u"liz@royal.gov.uk",
                postcode=u"SW1A 1AA"
            )
        )
        db.session.commit()

    def _post_dos_draft(self, draft_json=None):
        res = self.client.post(
            '/draft-services',
            data=json.dumps(draft_json or self.create_draft_json),
            content_type='application/json')
        assert res.status_code == 201, res.get_data()
        return res

    def _edit_dos_draft(self, draft_id, services, page_questions=None):
        res = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps({
                'updated_by': 'joeblogs',
                'services': services,
                'page_questions': page_questions if page_questions is not None else []
            }),
            content_type='application/json')
        return res

    def test_should_create_dos_draft_with_minimal_data(self):
        res = self._post_dos_draft()

        data = json.loads(res.get_data())
        assert data['services']['frameworkSlug'] == 'digital-outcomes-and-specialists'
        assert data['services']['frameworkName'] == 'Digital Outcomes and Specialists'
        assert data['services']['status'] == 'not-submitted'
        assert data['services']['supplierId'] == 1
        assert data['services']['lot'] == 'digital-specialists'

    def test_disallow_multiple_drafts_for_one_service_lots(self):
        self._post_dos_draft()

        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert res.status_code == 400
        assert data['error'] == "'digital-specialists' service already exists for supplier '1'"

    def test_allow_multiple_drafts_for_one_service_lots_on_different_frameworks(self):
        self.setup_dummy_framework(
            slug='digital-outcomes-and-specialists-2',
            framework_family='digital-outcomes-and-specialists',
            name='Digital Outcomes and Specialists 2',
            id=101,
        )
        self._post_dos_draft()

        dos_2_draft = self.create_draft_json.copy()
        dos_2_draft['services']['frameworkSlug'] = 'digital-outcomes-and-specialists-2'
        res = self.client.post(
            '/draft-services',
            data=json.dumps(dos_2_draft),
            content_type='application/json')
        assert res.status_code == 201, res.get_data()

        data = json.loads(res.get_data())
        assert data['services']['frameworkSlug'] == 'digital-outcomes-and-specialists-2'
        assert data['services']['frameworkName'] == 'Digital Outcomes and Specialists 2'
        assert data['services']['status'] == 'not-submitted'
        assert data['services']['supplierId'] == 1
        assert data['services']['lot'] == 'digital-specialists'

    def test_create_dos_draft_should_create_audit_event(self):
        res = self._post_dos_draft()

        data = json.loads(res.get_data())
        draft_id = data['services']['id']

        res = self.client.get('/audit-events')
        assert res.status_code == 200

        all_audit_events = res.json['auditEvents']
        assert len(all_audit_events) == 1
        assert all_audit_events[0]['user'] == 'joeblogs'
        assert all_audit_events[0]['type'] == 'create_draft_service'
        assert all_audit_events[0]['data']['draftId'] == draft_id

        res = self.client.get(f"/audit-events?data-draft-service-id={draft_id}")
        assert res.status_code == 200

        draft_service_audit_events = res.json["auditEvents"]
        assert all_audit_events == draft_service_audit_events

    def test_should_fetch_a_dos_draft(self):
        res = self._post_dos_draft()
        draft_id = json.loads(res.get_data())['services']['id']
        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        assert fetch.status_code == 200
        data = json.loads(res.get_data())
        assert data['services']['dataProtocols'] is True
        assert data['services']['id'] == draft_id

    def test_should_delete_a_dos_draft(self):
        res = self._post_dos_draft()
        draft_id = json.loads(res.get_data())['services']['id']
        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        assert fetch.status_code == 200
        delete = self.client.delete(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert delete.status_code == 200

        res = self.client.get('/audit-events')
        assert res.status_code == 200

        all_audit_events = res.json['auditEvents']
        assert len(all_audit_events) == 2
        assert all_audit_events[0]['type'] == 'create_draft_service'
        assert all_audit_events[1]['user'] == 'joeblogs'
        assert all_audit_events[1]['type'] == 'delete_draft_service'
        assert all_audit_events[1]['data']['draftId'] == draft_id

        res = self.client.get(f"/audit-events?data-draft-service-id={draft_id}")
        assert res.status_code == 200

        draft_service_audit_events = res.json["auditEvents"]
        assert all_audit_events == draft_service_audit_events

        fetch_again = self.client.get(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert fetch_again.status_code == 404

    def test_should_edit_dos_draft(self):
        res = self._post_dos_draft()
        draft_id = json.loads(res.get_data())['services']['id']
        update = self._edit_dos_draft(
            draft_id=draft_id,
            services={'dataProtocols': False}
        )
        assert update.status_code == 200

        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        assert fetch.status_code == 200
        data = json.loads(fetch.get_data())
        assert data['services']['dataProtocols'] is False
        assert data['services']['id'] == draft_id

    def test_should_not_edit_draft_with_invalid_price_strings(self):
        res = self._post_dos_draft()
        draft_id = json.loads(res.get_data())['services']['id']
        update = self._edit_dos_draft(
            draft_id=draft_id,
            services={
                "agileCoachPriceMin": 'not_a_valid_price',
                "agileCoachPriceMax": '!@#$%^&*('},
            page_questions=[]
        )
        data = json.loads(update.get_data())
        for key in ['agileCoachPriceMin', 'agileCoachPriceMax']:
            assert data['error'][key] == 'not_money_format'
        assert update.status_code == 400

    def test_should_not_edit_draft_with_max_price_less_than_min_price(self):
        res = self._post_dos_draft()
        draft_id = json.loads(res.get_data())['services']['id']
        update = self._edit_dos_draft(
            draft_id=draft_id,
            services={
                "agileCoachPriceMin": '200',
                "agileCoachPriceMax": '100'},
            page_questions=[]
        )
        data = json.loads(update.get_data())
        assert data['error']['agileCoachPriceMax'] == 'max_less_than_min'
        assert update.status_code == 400

    def test_should_not_edit_draft_if_dependencies_missing(self):
        res = self._post_dos_draft()
        draft_id = json.loads(res.get_data())['services']['id']
        update = self._edit_dos_draft(
            draft_id=draft_id,
            services={
                # missing "developerLocations"
                "dataProtocols": True,
                "developerPriceMin": "1"},
            page_questions=["dataProtocols", "developerPriceMin"],
        )
        data = json.loads(update.get_data())
        for key in ['developerLocations', 'developerPriceMax']:
            assert data['error'][key] == 'answer_required'
        assert update.status_code == 400

    def test_should_filter_out_invalid_page_questions(self):
        res = self._post_dos_draft()
        draft_id = json.loads(res.get_data())['services']['id']
        update = self._edit_dos_draft(
            draft_id=draft_id,
            services={
                "dataProtocols": True},
            page_questions=[
                # neither of these keys exist in the schema
                "clemenule",
                "firecracker",
                # keys which exist in anyOf requirements are ignored
                "developerLocations",
                "developerPriceMax",
                "developerPriceMin"]
        )
        assert update.status_code == 200

    def test_should_not_copy_one_service_limit_lot_draft(self):
        draft = json.loads(self._post_dos_draft().get_data())

        res = self.client.post(
            '/draft-services/{}/copy'.format(draft['services']['id']),
            data=json.dumps({"updated_by": "me"}),
            content_type="application/json")
        data = json.loads(res.get_data())

        assert res.status_code == 400
        assert "Cannot copy a 'digital-specialists' draft" in data['error']

    def test_complete_valid_dos_draft(self):
        res = self._post_dos_draft()
        draft_id = json.loads(res.get_data())['services']['id']
        complete = self.client.post(
            '/draft-services/{}/complete'.format(draft_id),
            data=json.dumps(self.updater_json),
            content_type='application/json'
        )
        assert complete.status_code == 200

    def test_should_not_complete_invalid_dos_draft(self):
        draft_json = self.create_draft_json
        draft_json['services'].pop('agileCoachLocations')
        draft_json['services'].pop('agileCoachPriceMin')
        draft_json['services'].pop('agileCoachPriceMax')
        res = self._post_dos_draft(draft_json)
        draft_id = json.loads(res.get_data())['services']['id']
        complete = self.client.post(
            '/draft-services/{}/complete'.format(draft_id),
            data=json.dumps(self.updater_json),
            content_type='application/json'
        )
        data = json.loads(complete.get_data())
        assert "specialist_required" in "{}".format(data['error']['_form'])
        assert complete.status_code == 400


class TestUpdateDraftStatus(BaseApplicationTest, JSONUpdateTestMixin):
    endpoint = '/draft-services/{self.draft_id}/update-status'
    method = 'post'

    def setup(self):
        super(TestUpdateDraftStatus, self).setup()

        db.session.add(Supplier(supplier_id=1, name=u"Supplier 1"))
        db.session.add(
            ContactInformation(
                supplier_id=1,
                contact_name=u"Test",
                email=u"supplier@user.dmdev",
                postcode=u"SW1A 1AA"
            )
        )
        Framework.query.filter_by(slug='g-cloud-7').update(dict(status='open'))
        db.session.commit()
        draft_json = load_example_listing("G7-SCS")
        draft_json['frameworkSlug'] = 'g-cloud-7'
        create_draft_json = {
            'updated_by': 'joeblogs',
            'services': draft_json
        }

        draft = self.client.post(
            '/draft-services',
            data=json.dumps(create_draft_json),
            content_type='application/json')

        self.draft = json.loads(draft.get_data())['services']
        self.draft_id = self.draft['id']

    def test_update_draft_status(self):
        res = self.client.post(
            '/draft-services/{}/update-status'.format(self.draft_id),
            data=json.dumps({'services': {'status': 'failed'}, 'updated_by': 'joeblogs'}),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert res.status_code == 200, res.get_data()
        assert data['services']['status'] == 'failed'

    def test_update_draft_status_should_create_audit_event(self):
        res = self.client.post(
            '/draft-services/{}/update-status'.format(self.draft_id),
            data=json.dumps({'services': {'status': 'failed'}, 'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert res.status_code == 200

        res = self.client.get('/audit-events')
        assert res.status_code == 200

        all_audit_events = res.json['auditEvents']
        assert len(all_audit_events) == 2
        assert all_audit_events[1]['user'] == 'joeblogs'
        assert all_audit_events[1]['type'] == 'update_draft_service_status'
        assert all_audit_events[1]['data'] == {
            'draftId': self.draft_id,
            'status': 'failed',
            'supplierId': 1,
        }

        res = self.client.get(f"/audit-events?data-draft-service-id={self.draft_id}")
        assert res.status_code == 200

        draft_service_audit_events = res.json["auditEvents"]
        assert all_audit_events == draft_service_audit_events

    def test_should_not_update_draft_status_to_invalid_status(self):
        res = self.client.post(
            '/draft-services/{}/update-status'.format(self.draft_id),
            data=json.dumps({'services': {'status': 'INVALID-STATUS'}, 'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert res.status_code == 400
        assert json.loads(res.get_data()) == {"error": "'INVALID-STATUS' is not a valid status"}

    @mock.patch('app.db.session.commit')
    def test_update_draft_status_catches_db_integrity_errors(self, db_commit):
        db_commit.side_effect = IntegrityError("Could not commit", orig=None, params={})
        res = self.client.post(
            '/draft-services/{}/update-status'.format(self.draft_id),
            data=json.dumps({'services': {'status': 'failed'}, 'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert res.status_code == 400
        assert "Could not commit" in json.loads(res.get_data())['error']
