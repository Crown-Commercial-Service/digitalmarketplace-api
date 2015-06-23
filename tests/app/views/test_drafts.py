from tests.app.helpers import BaseApplicationTest
from datetime import datetime
from flask import json
from app.models import Supplier, ContactInformation, Service, Framework
from app import db

from nose.tools import assert_equal, assert_in


class TestDraftServices(BaseApplicationTest):
    service_id = None
    updater_json = None
    create_draft_json = None

    def setup(self):
        super(TestDraftServices, self).setup()

        payload = self.load_example_listing("G6-IaaS")

        self.service_id = str(payload['id'])
        self.updater_json = {
            'update_details': {
                'updated_by': 'joeblogs'}
        }
        self.create_draft_json = self.updater_json.copy()
        self.create_draft_json['services'] = {
            'lot': 'SCS',
            'supplierId': 1
        }

        with self.app.app_context():
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

        self.client.put(
            '/services/%s' % self.service_id,
            data=json.dumps(
                {'update_details': {
                    'updated_by': 'joeblogs'},
                 'services': payload}),
            content_type='application/json')

    def test_reject_list_drafts_no_supplier_id(self):
        res = self.client.get('/services/draft')
        assert_equal(res.status_code, 400)

    def test_reject_list_drafts_invalid_supplier_id(self):
        res = self.client.get('/services/draft?supplier_id=invalid')
        assert_equal(res.status_code, 400)

    def test_reject_list_drafts_if_no_supplier_for_id(self):
        res = self.client.get('/draft-services?supplier_id=12345667')
        assert_equal(res.status_code, 404)

    def test_returns_empty_list_if_no_drafts(self):
        res = self.client.get('/draft-services?supplier_id=1')
        assert_equal(res.status_code, 200)
        drafts = json.loads(res.get_data())
        assert_equal(len(drafts['services']), 0)

    def test_returns_drafts_for_supplier(self):
        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        res = self.client.get('/draft-services?supplier_id=1')
        assert_equal(res.status_code, 200)
        drafts = json.loads(res.get_data())
        assert_equal(len(drafts['services']), 1)

    def test_returns_drafts_for_framework_with_drafts(self):
        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        res = self.client.get(
            '/draft-services?supplier_id=1&framework=g-cloud-6'
        )
        assert_equal(res.status_code, 200)
        drafts = json.loads(res.get_data())
        assert_equal(len(drafts['services']), 1)

    def test_does_not_return_drafts_for_framework_with_no_drafts(self):
        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        res = self.client.get(
            '/draft-services?supplier_id=1&framework=g-cloud-7'
        )
        assert_equal(res.status_code, 200)
        drafts = json.loads(res.get_data())
        assert_equal(len(drafts['services']), 0)

    def test_returns_all_drafts_for_supplier_on_single_page(self):
        with self.app.app_context():

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
                        service_id=service_id,
                        supplier_id=1,
                        updated_at=now,
                        status='published',
                        created_at=now,
                        data={'foo': 'bar'},
                        framework_id=1)
                )

            for service_id in service_ids:
                self.client.put(
                    '/draft-services/copy-from/{}'.format(service_id),
                    data=json.dumps(self.updater_json),
                    content_type='application/json')

            res = self.client.get('/draft-services?supplier_id=1')
            assert_equal(res.status_code, 200)
            drafts = json.loads(res.get_data())
            assert_equal(len(drafts['services']), 10)

    def test_returns_drafts_for_supplier_has_no_links(self):
        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        res = self.client.get('/draft-services?supplier_id=1')
        assert_equal(res.status_code, 200)
        drafts = json.loads(res.get_data())
        assert_equal(len(drafts['links']), 0)

    def test_reject_update_with_no_updater_details(self):
        res = self.client.post('/draft-services/0000000000')

        assert_equal(res.status_code, 400)

    def test_reject_copy_with_no_update_details(self):
        res = self.client.put('/draft-services/copy-from/0000000000')

        assert_equal(res.status_code, 400)

    def test_reject_create_with_no_update_details(self):
        res = self.client.post('/draft-services/g-cloud-7/create')

        assert_equal(res.status_code, 400)

    def test_reject_invalid_service_id_on_copy(self):
        res = self.client.put(
            '/draft-services/copy-from/invalid-id!',
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert_equal(res.status_code, 400)

    def test_should_404_if_service_does_not_exist_on_copy(self):
        res = self.client.put(
            '/draft-services/copy-from/0000000000',
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert_equal(res.status_code, 404)

    def test_reject_invalid_service_id_on_get(self):
        res = self.client.get('/draft-services?service_id=invalid-id!')

        assert_equal(res.status_code, 400)

    def test_reject_delete_with_no_update_details(self):
        res = self.client.delete('/draft-services/0000000000')

        assert_equal(res.status_code, 400)

    def test_reject_publish_with_no_update_details(self):
        res = self.client.post('/draft-services/0000000000/publish')

        assert_equal(res.status_code, 400)

    def test_should_create_draft_with_minimal_data(self):
        res = self.client.post(
            '/draft-services/g-cloud-7/create',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert_equal(res.status_code, 201)
        assert_equal(data['services']['frameworkName'], 'G-Cloud 7')
        assert_equal(data['services']['status'], 'not-submitted')
        assert_equal(data['services']['supplierId'], 1)
        assert_equal(data['services']['lot'], 'SCS')

    def test_create_draft_should_create_audit_event(self):
        res = self.client.post(
            '/draft-services/g-cloud-7/create',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')

        assert_equal(res.status_code, 201)
        data = json.loads(res.get_data())
        draft_id = data['services']['id']

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())
        assert_equal(len(data['auditEvents']), 2)
        assert_equal(data['auditEvents'][0]['type'], 'import_service')
        assert_equal(data['auditEvents'][1]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][1]['type'], 'create_draft_service')
        assert_equal(
            data['auditEvents'][1]['data']['draft_id'], draft_id
        )

    def test_should_not_create_draft_with_invalid_data(self):
        invalid_create_json = self.create_draft_json.copy()
        invalid_create_json['services']['supplierId'] = "ShouldBeInt"
        res = self.client.post(
            '/draft-services/g-cloud-7/create',
            data=json.dumps(invalid_create_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert_equal(res.status_code, 400)
        assert_in("'ShouldBeInt' is not of type", data['errors']['supplierId'])

    def test_can_save_additional_fields_to_draft(self):
        res = self.client.post(
            '/draft-services/g-cloud-7/create',
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
        assert_equal(res2.status_code, 200)
        assert_equal(data2['services']['frameworkName'], 'G-Cloud 7')
        assert_equal(data2['services']['status'], 'not-submitted')
        assert_equal(data2['services']['supplierId'], 1)
        assert_equal(data2['services']['serviceTypes'], ['Implementation'])
        assert_equal(data2['services']['serviceBenefits'], ['Tests pass'])

    def test_update_draft_should_create_audit_event(self):
        res = self.client.post(
            '/draft-services/g-cloud-7/create',
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
        assert_equal(res2.status_code, 200)

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())
        assert_equal(len(data['auditEvents']), 3)
        assert_equal(data['auditEvents'][0]['type'], 'import_service')
        assert_equal(data['auditEvents'][1]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][1]['type'], 'create_draft_service')
        assert_equal(
            data['auditEvents'][1]['data']['draft_id'], draft_id
        )
        assert_equal(data['auditEvents'][2]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][2]['type'], 'update_draft_service')
        assert_equal(
            data['auditEvents'][2]['data']['draft_id'], draft_id
        )

    def test_validation_errors_returned_for_invalid_update_of_new_draft(self):
        res = self.client.post(
            '/draft-services/g-cloud-7/create',
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
        assert_equal(res2.status_code, 400)
        assert_in("'Bad Type' is not one of", data2['errors']['serviceTypes'])
        # 'Invalid value' is not one of

    def test_validation_errors_returned_for_invalid_update_of_copy(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        draft_id = json.loads(res.get_data())['services']['id']
        res = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs'},
                'services': {
                    'badField': 'new service name',
                    'priceUnit': 'chickens'
                }
            }),
            content_type='application/json')
        data = json.loads(res.get_data())
        assert_equal(res.status_code, 400)
        assert_in("'badField' was unexpected", str(data['errors']['_form']))
        assert_in("'chickens' is not one of", data['errors']['priceUnit'])

    def test_should_create_draft_from_existing_service(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        data = json.loads(res.get_data())

        assert_equal(res.status_code, 201)
        assert_equal(data['services']['service_id'], self.service_id)

    def test_create_draft_from_existing_should_create_audit_event(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert_equal(res.status_code, 201)

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())

        assert_equal(len(data['auditEvents']), 2)
        assert_equal(data['auditEvents'][0]['type'], 'import_service')
        assert_equal(data['auditEvents'][1]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][1]['type'], 'create_draft_service')
        assert_equal(
            data['auditEvents'][1]['data']['service_id'], self.service_id
        )

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

        assert_equal(res.status_code, 400)
        assert_in(
            'Draft already exists for service {}'.format(self.service_id),
            data['error'])

    def test_should_fetch_a_draft(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert_equal(res.status_code, 201)
        draft_id = json.loads(res.get_data())['services']['id']
        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        assert_equal(fetch.status_code, 200)
        data = json.loads(res.get_data())
        assert_equal(data['services']['service_id'], self.service_id)

    def test_should_404_on_fetch_a_draft_that_doesnt_exist(self):
        fetch = self.client.get('/draft-services/0000000000')
        assert_equal(fetch.status_code, 404)

    def test_should_404_on_delete_a_draft_that_doesnt_exist(self):
        res = self.client.delete(
            '/draft-services/0000000000',
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert_equal(res.status_code, 404)

    def test_should_delete_a_draft(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert_equal(res.status_code, 201)
        draft_id = json.loads(res.get_data())['services']['id']
        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        assert_equal(fetch.status_code, 200)
        delete = self.client.delete(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert_equal(delete.status_code, 200)

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())

        assert_equal(len(data['auditEvents']), 3)
        assert_equal(data['auditEvents'][0]['type'], 'import_service')
        assert_equal(data['auditEvents'][1]['type'], 'create_draft_service')
        assert_equal(data['auditEvents'][2]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][2]['type'], 'delete_draft_service')
        assert_equal(
            data['auditEvents'][2]['data']['service_id'], self.service_id
        )

        fetch_again = self.client.get(
            '/draft-services/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert_equal(fetch_again.status_code, 404)

    def test_should_be_able_to_update_a_draft(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        draft_id = json.loads(res.get_data())['services']['id']
        update = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs'},
                'services': {
                    'serviceName': 'new service name'
                }
            }),
            content_type='application/json')

        data = json.loads(update.get_data())
        assert_equal(update.status_code, 200)
        assert_equal(data['services']['serviceName'], 'new service name')

        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        data = json.loads(fetch.get_data())
        assert_equal(fetch.status_code, 200)
        assert_equal(data['services']['serviceName'], 'new service name')

    def test_should_edit_draft_with_audit_event(self):
        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        draft_id = json.loads(res.get_data())['services']['id']
        update = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs'},
                'services': {
                    'serviceName': 'new service name'
                }
            }),
            content_type='application/json')
        assert_equal(update.status_code, 200)

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())

        assert_equal(len(data['auditEvents']), 3)
        assert_equal(data['auditEvents'][0]['type'], 'import_service')
        assert_equal(data['auditEvents'][2]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][2]['type'], 'update_draft_service')
        assert_equal(
            data['auditEvents'][2]['data']['service_id'], self.service_id
        )
        assert_equal(
            data['auditEvents'][2]['data']['update_json']['serviceName'],
            'new service name'
        )

    def test_should_be_a_400_if_no_service_block_in_update(self):
        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        update = self.client.post(
            '/draft-services/{}'.format(self.service_id),
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs'}
            }),
            content_type='application/json')

        assert_equal(update.status_code, 400)

    def test_should_not_be_able_to_publish_if_no_draft_exists(self):
        res = self.client.post(
            '/draft-services/98765/publish',
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs',
                }
            }),
            content_type='application/json')
        assert_equal(res.status_code, 404)

    def test_should_be_able_to_launch_valid_draft_service(self):
        initial = self.client.get('/services/{}'.format(self.service_id))
        assert_equal(initial.status_code, 200)
        assert_equal(
            json.loads(initial.get_data())['services']['serviceName'],
            'My Iaas Service')

        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        draft_id = json.loads(res.get_data())['services']['id']
        first_draft = self.client.get(
            '/draft-services/{}'.format(draft_id))
        assert_equal(first_draft.status_code, 200)
        assert_equal(
            json.loads(first_draft.get_data())['services']['serviceName'],
            'My Iaas Service')

        self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs'},
                'services': {
                    'serviceName': 'chickens'
                }
            }),
            content_type='application/json')

        updated_draft = self.client.get(
            '/draft-services/{}'.format(draft_id))
        assert_equal(updated_draft.status_code, 200)
        assert_equal(
            json.loads(updated_draft.get_data())['services']['serviceName'],
            'chickens')

        res = self.client.post(
            '/draft-services/{}/publish'.format(draft_id),
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs',
                }
            }),
            content_type='application/json')
        assert_equal(res.status_code, 200)

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())

        assert_equal(len(data['auditEvents']), 4)
        assert_equal(data['auditEvents'][0]['type'], 'import_service')
        assert_equal(data['auditEvents'][1]['type'], 'create_draft_service')
        assert_equal(data['auditEvents'][2]['type'], 'update_draft_service')
        assert_equal(data['auditEvents'][3]['type'], 'publish_draft_service')

        # draft should no longer exist
        fetch = self.client.get('/draft-services/{}'.format(self.service_id))
        assert_equal(fetch.status_code, 404)

        # published should be updated
        updated_draft = self.client.get('/services/{}'.format(self.service_id))
        assert_equal(updated_draft.status_code, 200)
        assert_equal(
            json.loads(updated_draft.get_data())['services']['serviceName'],
            'chickens')

        # archive should be updated
        archives = self.client.get(
            '/archived-services?service-id={}'.format(self.service_id))
        assert_equal(archives.status_code, 200)
        assert_equal(
            json.loads(archives.get_data())['services'][0]['serviceName'],
            'My Iaas Service')
