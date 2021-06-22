from tests.app.helpers import BaseApplicationTest, JSONUpdateTestMixin
from datetime import datetime
from flask import json
import mock
from app.models import Supplier, Service, Framework, DraftService, Address
from app import db

from nose.tools import assert_equal, assert_in, assert_false


class TestDraftServices(BaseApplicationTest):
    service_id = None
    updater_json = None
    create_draft_json = None

    def setup(self):
        super(TestDraftServices, self).setup()

        payload = self.load_example_listing("G6-IaaS")

        self.service_id = str(payload['id'])
        self.updater_json = {
            'updated_by': 'joeblogs'
        }
        self.create_draft_json = self.updater_json.copy()
        self.create_draft_json['services'] = {
            'frameworkSlug': 'g-cloud-7',
            'lot': 'scs',
            'supplierCode': 1
        }

        with self.app.app_context():
            db.session.add(
                Supplier(code=1, name="Supplier 1",
                         addresses=[Address(address_line="{} Dummy Street 1",
                                            suburb="Dummy",
                                            state="ZZZ",
                                            postal_code="0000",
                                            country='Australia')])
            )
            Framework.query.filter_by(slug='g-cloud-5') \
                .update(dict(status='live'))
            Framework.query.filter_by(slug='g-cloud-7') \
                .update(dict(status='open'))
            db.session.commit()

        self.client.put(
            '/services/%s' % self.service_id,
            data=json.dumps(
                {'updated_by': 'joeblogs',
                 'services': payload}),
            content_type='application/json')

    def service_count(self):
        with self.app.app_context():
            return Service.query.count()

    def draft_service_count(self):
        with self.app.app_context():
            return DraftService.query.count()

    def test_reject_list_drafts_no_supplier_code(self):

        res = self.client.get('/draft-services')
        assert_equal(res.status_code, 400)

    def test_reject_list_drafts_invalid_supplier_code(self):

        res = self.client.get('/draft-services?supplier_code=invalid')
        assert_equal(res.status_code, 400)

    def test_reject_list_drafts_if_no_supplier_for_id(self):

        res = self.client.get('/draft-services?supplier_code=12345667')
        assert_equal(res.status_code, 404)

    def test_returns_empty_list_if_no_drafts(self):

        res = self.client.get('/draft-services?supplier_code=1')
        assert_equal(res.status_code, 200)
        drafts = json.loads(res.get_data())
        assert_equal(len(drafts['services']), 0)

    def test_returns_drafts_for_supplier(self):

        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        res = self.client.get('/draft-services?supplier_code=1')
        assert_equal(res.status_code, 200)
        drafts = json.loads(res.get_data())
        assert_equal(len(drafts['services']), 1)

    def test_returns_drafts_for_framework_with_drafts(self):

        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        res = self.client.get(
            '/draft-services?supplier_code=1&framework=g-cloud-6'
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
            '/draft-services?supplier_code=1&framework=g-cloud-7'
        )
        assert_equal(res.status_code, 200)
        drafts = json.loads(res.get_data())
        assert_equal(len(drafts['services']), 0)

    def test_does_not_return_drafts_from_non_existant_framework(self):

        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        res = self.client.get(
            '/draft-services?supplier_code=1&framework=this-is-not-valid'
        )
        assert res.status_code == 404
        assert json.loads(res.get_data(as_text=True))["error"] == "framework 'this-is-not-valid' not found"

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
                        service_id=str(service_id),
                        supplier_code=1,
                        updated_at=now,
                        status='published',
                        created_at=now,
                        data={'foo': 'bar'},
                        lot_id=1,
                        framework_id=1)
                )

            for service_id in service_ids:
                self.client.put(
                    '/draft-services/copy-from/{}'.format(service_id),
                    data=json.dumps(self.updater_json),
                    content_type='application/json')

            res = self.client.get('/draft-services?supplier_code=1')
            assert_equal(res.status_code, 200)
            drafts = json.loads(res.get_data())
            assert_equal(len(drafts['services']), 10)

    def test_returns_drafts_for_supplier_has_no_links(self):

        self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        res = self.client.get('/draft-services?supplier_code=1')
        assert_equal(res.status_code, 200)
        drafts = json.loads(res.get_data())
        assert_equal(len(drafts['links']), 0)

    def test_reject_update_with_no_updater_details(self):

        res = self.client.post('/draft-services/0000000000')

        assert_equal(res.status_code, 400)

    def test_reject_copy_with_no_updated_by(self):

        res = self.client.put('/draft-services/copy-from/0000000000')

        assert_equal(res.status_code, 400)

    def test_reject_create_with_no_updated_by(self):

        res = self.client.post('/draft-services')

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

    def test_reject_delete_with_no_updated_by(self):

        res = self.client.delete('/draft-services/0000000000',
                                 data=json.dumps({}),
                                 content_type='application/json')

        assert_equal(res.status_code, 400)

    def test_reject_publish_with_no_updated_by(self):

        res = self.client.post('/draft-services/0000000000/publish',
                               data=json.dumps({}),
                               content_type='application/json')

        assert_equal(res.status_code, 400)

    def test_should_create_draft_with_minimal_data(self):

        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert_equal(res.status_code, 201)
        assert_equal(data['services']['frameworkSlug'], 'g-cloud-7')
        assert_equal(data['services']['frameworkName'], 'G-Cloud 7')
        assert_equal(data['services']['status'], 'not-submitted')
        assert_equal(data['services']['supplierCode'], 1)
        assert_equal(data['services']['lot'], 'scs')

    def test_create_draft_checks_page_questions(self):

        self.create_draft_json['page_questions'] = ['serviceName']
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert_equal(res.status_code, 400)
        assert_equal(data['error'], {'serviceName': 'answer_required'})

    def test_create_draft_only_checks_valid_page_questions(self):

        self.create_draft_json['page_questions'] = ['tea_and_cakes']
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')

        assert_equal(res.status_code, 201)

    def test_create_draft_should_create_audit_event(self):

        res = self.client.post(
            '/draft-services',
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
        assert_equal(data['auditEvents'][1]['data']['draftId'], draft_id)
        assert_equal(data['auditEvents'][1]['data']['draftJson'], self.create_draft_json['services'])

    def test_should_not_create_draft_with_invalid_data(self):

        invalid_create_json = self.create_draft_json.copy()
        invalid_create_json['services']['supplierCode'] = "ShouldBeInt"
        res = self.client.post(
            '/draft-services',
            data=json.dumps(invalid_create_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert_equal(res.status_code, 400)
        assert_in("Invalid supplier Code 'ShouldBeInt'", data['error'])

    def test_should_not_create_draft_on_not_open_framework(self):

        draft_json = self.create_draft_json.copy()
        draft_json['services']['frameworkSlug'] = 'g-cloud-5'
        res = self.client.post(
            '/draft-services',
            data=json.dumps(draft_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert_equal(res.status_code, 400)
        assert_in("'g-cloud-5' is not open for submissions", data['error'])

    def test_should_not_create_draft_with_invalid_lot(self):

        draft_json = self.create_draft_json.copy()
        draft_json['services']['lot'] = 'newlot'
        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert_equal(res.status_code, 400)
        assert_in("Incorrect lot 'newlot' for framework 'g-cloud-7'", data['error'])

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
        assert_equal(res2.status_code, 200)
        assert_equal(data2['services']['frameworkSlug'], 'g-cloud-7')
        assert_equal(data2['services']['frameworkName'], 'G-Cloud 7')
        assert_equal(data2['services']['status'], 'not-submitted')
        assert_equal(data2['services']['supplierCode'], 1)
        assert_equal(data2['services']['serviceTypes'], ['Implementation'])
        assert_equal(data2['services']['serviceBenefits'], ['Tests pass'])

    @mock.patch('app.db')
    def test_update_draft_uses_serializable_isolation_level(self, db):

        self.client.post('/draft-services/1234')
        db.session.connection.assert_called_with(execution_options={'isolation_level': 'SERIALIZABLE'})

    def test_update_draft_should_create_audit_event(self):

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
        assert_equal(res2.status_code, 200)

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())
        assert_equal(len(data['auditEvents']), 3)
        assert_equal(data['auditEvents'][0]['type'], 'import_service')
        assert_equal(data['auditEvents'][1]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][1]['type'], 'create_draft_service')
        assert_equal(
            data['auditEvents'][1]['data']['draftId'], draft_id
        )
        assert_equal(data['auditEvents'][2]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][2]['type'], 'update_draft_service')
        assert_equal(
            data['auditEvents'][2]['data']['draftId'], draft_id
        )

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
        assert_equal(res2.status_code, 200)
        data2 = json.loads(res2.get_data())['services']
        assert ('serviceName' in data2)
        assert ('serviceBenefits' in data2)
        assert ('serviceTypes' in data2)

        draft_update_json['services'] = {
            'serviceTypes': None,
            'serviceBenefits': None
        }
        res3 = self.client.post(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(draft_update_json),
            content_type='application/json')
        print(res3.data)
        assert_equal(res3.status_code, 200)
        data3 = json.loads(res3.get_data())['services']
        assert ('serviceName' in data3)
        assert ('serviceBenefits' not in data3)
        assert ('serviceTypes' not in data3)

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

        assert_equal(res2.status_code, 400)
        assert_equal(errors, {'serviceName': 'answer_required', 'serviceBenefits': 'answer_required'})

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

        assert_equal(res2.status_code, 200)
        assert_equal(updated_draft['status'], 'not-submitted')
        assert ('serviceName' not in updated_draft)
        assert ('serviceBenefits' not in updated_draft)

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
        assert_equal(res2.status_code, 400)
        assert_in("'Bad Type' is not one of", data2['error']['serviceTypes'])

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
        assert_equal(res.status_code, 400)
        assert_in("'badField' was unexpected", str(data['error']['_form']))
        assert_in("no_unit_specified", data['error']['priceUnit'])

    def test_should_create_draft_from_existing_service(self):

        res = self.client.put(
            '/draft-services/copy-from/{}'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        data = json.loads(res.get_data())

        assert_equal(res.status_code, 201)
        assert_equal(data['services']['serviceId'], self.service_id)

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
            data['auditEvents'][1]['data']['serviceId'], self.service_id
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

    def test_submission_draft_should_not_prevent_draft_being_created_from_existing_service(self):

        res = self.publish_new_draft_service()

        service = json.loads(res.get_data())['services']

        res = self.client.put(
            '/draft-services/copy-from/{}'.format(service['id']),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert res.status_code == 201

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
        assert_equal(data['services']['serviceId'], self.service_id)

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
            data['auditEvents'][2]['data']['serviceId'], self.service_id
        )

        fetch_again = self.client.get('/draft-services/{}'.format(draft_id))
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
                'updated_by': 'joeblogs',
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
        assert_equal(update.status_code, 200)
        assert_equal(data['services']['serviceName'], 'a new  service name')

        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        data = json.loads(fetch.get_data())
        assert_equal(fetch.status_code, 200)
        assert_equal(data['services']['serviceName'], 'a new  service name')
        assert_equal(len(data['services']['serviceFeatures']), 2)
        assert_equal(data['services']['serviceFeatures'][0], 'Feature   1')
        assert_equal(data['services']['serviceFeatures'][1], 'second feature')

    def test_should_edit_draft_with_audit_event(self):

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
        assert_equal(update.status_code, 200)

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())

        assert_equal(len(data['auditEvents']), 3)
        assert_equal(data['auditEvents'][0]['type'], 'import_service')
        assert_equal(data['auditEvents'][2]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][2]['type'], 'update_draft_service')
        assert_equal(
            data['auditEvents'][2]['data']['serviceId'], self.service_id
        )
        assert_equal(
            data['auditEvents'][2]['data']['updateJson']['serviceName'],
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
                'updated_by': 'joeblogs'
            }),
            content_type='application/json')

        assert_equal(update.status_code, 400)

    def test_should_not_be_able_to_publish_if_no_draft_exists(self):

        res = self.client.post(
            '/draft-services/98765/publish',
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')
        assert_equal(res.status_code, 404)

    @mock.patch('app.service_utils.search_api_client')
    def test_should_be_able_to_publish_valid_copied_draft_service(self, search_api_client):

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
                'updated_by': 'joeblogs',
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
            data=json.dumps({'updated_by': 'joeblogs'}),
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

        assert search_api_client.index.called

    def test_should_not_be_able_to_publish_submission_if_not_submitted(self):

        draft = self.create_draft_service()

        res = self.publish_draft_service(draft['id'])
        assert_equal(res.status_code, 400)

    def test_should_not_be_able_to_republish_submission(self):

        draft = self.create_draft_service()
        self.complete_draft_service(draft['id'])

        res = self.publish_draft_service(draft['id'])
        assert_equal(res.status_code, 200)

        res = self.publish_draft_service(draft['id'])
        assert_equal(res.status_code, 400)

    @mock.patch('app.service_utils.search_api_client')
    def test_search_api_should_be_called_on_publish_if_framework_is_live(self, search_api_client):

        draft_id = self.create_draft_service()['id']
        self.complete_draft_service(draft_id)

        with self.app.app_context():
            Framework.query.filter_by(slug='g-cloud-7').update(dict(status='live'))
            db.session.commit()

        res = self.publish_draft_service(draft_id)

        assert res.status_code == 200
        assert search_api_client.index.called

    @mock.patch('app.service_utils.search_api_client')
    def test_should_be_able_to_publish_valid_new_draft_service(self, search_api_client):

        draft_id = self.create_draft_service()['id']
        self.complete_draft_service(draft_id)

        res = self.publish_draft_service(draft_id)

        assert_equal(res.status_code, 200)
        created_service_data = json.loads(res.get_data())
        new_service_id = created_service_data['services']['id']

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())
        assert_equal(len(data['auditEvents']), 5)
        assert_equal(data['auditEvents'][0]['type'], 'import_service')
        assert_equal(data['auditEvents'][1]['type'], 'create_draft_service')
        assert_equal(data['auditEvents'][2]['type'], 'update_draft_service')
        assert_equal(data['auditEvents'][3]['type'], 'complete_draft_service')
        assert_equal(data['auditEvents'][4]['type'], 'publish_draft_service')

        # draft should still exist
        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        assert_equal(fetch.status_code, 200)

        # G-Cloud 7 service should be visible from API
        # (frontends hide them based on statuses)
        fetch2 = self.client.get('/services/{}'.format(new_service_id))
        assert_equal(fetch2.status_code, 200)
        assert_equal(json.loads(fetch2.get_data())['services']['status'],
                     "published")

        # archive should be updated
        archives = self.client.get(
            '/archived-services?service-id={}'.format(new_service_id))
        assert_equal(archives.status_code, 200)
        assert_equal(
            json.loads(archives.get_data())['services'][0]['serviceName'],
            'An example G-7 SCS Service')

        # service should not be indexed as G-Cloud 7 is not live
        assert not search_api_client.index.called

    def create_draft_service(self):

        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')
        assert_equal(res.status_code, 201)
        draft = json.loads(res.get_data())['services']

        g7_complete = self.load_example_listing("G7-SCS").copy()
        g7_complete.pop('id')
        draft_update_json = {'services': g7_complete,
                             'updated_by': 'joeblogs'}
        res2 = self.client.post(
            '/draft-services/{}'.format(draft['id']),
            data=json.dumps(draft_update_json),
            content_type='application/json')
        assert_equal(res2.status_code, 200)
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

    def test_submitted_drafts_are_not_deleted_when_published(self):

        draft = self.create_draft_service()
        self.complete_draft_service(draft['id'])

        assert self.draft_service_count() == 1
        assert self.publish_draft_service(draft['id']).status_code == 200
        assert self.draft_service_count() == 1

    def test_drafts_made_from_services_are_deleted_when_published(self):

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

    @mock.patch('app.models.generate_new_service_id')
    def test_service_id_collisions_should_be_handled(self, generate_new_service_id):

        # Return the same ID a few times (cause collisions) and then return
        # a different one.
        generate_new_service_id.side_effect = [
            '1234567890123457',
            '1234567890123457',
            '1234567890123457',
            '1234567890123458',
        ]

        res = self.publish_new_draft_service()
        assert_equal(res.status_code, 200)
        res = self.publish_new_draft_service()
        assert_equal(res.status_code, 200)

        # Count is 3 because we create one in the setup
        assert self.service_count() == 3
        res = self.client.get('/services?framework=g-cloud-7')
        services = json.loads(res.get_data())['services']
        assert services[0]['id'] == '1234567890123457'
        assert services[1]['id'] == '1234567890123458'
        assert self.draft_service_count() == 2

    def test_get_draft_returns_last_audit_event(self):

        draft = json.loads(self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json'
        ).get_data())['services']

        res = self.client.get(
            '/draft-services/%d' % draft['id'],
            data=json.dumps(self.create_draft_json),
            content_type='application/json'
        )

        assert_equal(res.status_code, 200)
        data = json.loads(res.get_data())
        draft, audit_event = data['services'], data['auditEvents']

        assert_equal(audit_event['type'], 'create_draft_service')


class TestCopyDraft(BaseApplicationTest, JSONUpdateTestMixin):
    endpoint = '/draft-services/{self.draft_id}/copy'
    method = 'post'
    draft_id = 0

    def setup(self):
        super(TestCopyDraft, self).setup()

        with self.app.app_context():
            db.session.add(
                Supplier(code=1, name="Supplier 1",
                         addresses=[Address(address_line="{} Dummy Street 1",
                                            suburb="Dummy",
                                            state="ZZZ",
                                            postal_code="0000",
                                            country='Australia')])
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
                'supplierCode': 1,
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
            '/draft-services/%s/copy' % self.draft_id,
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert_equal(res.status_code, 201, res.get_data())
        assert_equal(data['services']['lot'], 'scs')
        assert_equal(data['services']['status'], 'not-submitted')
        assert_equal(data['services']['serviceName'], 'Draft copy')
        assert_equal(data['services']['supplierCode'], 1)
        assert_equal(data['services']['frameworkSlug'], self.draft['frameworkSlug'])
        assert_equal(data['services']['frameworkName'], self.draft['frameworkName'])

    def test_copy_draft_should_create_audit_event(self):
        res = self.client.post(
            '/draft-services/%s/copy' % self.draft_id,
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert_equal(res.status_code, 201)
        data = json.loads(res.get_data())
        draft_id = data['services']['id']

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())
        assert_equal(len(data['auditEvents']), 2)
        assert_equal(data['auditEvents'][1]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][1]['type'], 'create_draft_service')
        assert_equal(data['auditEvents'][1]['data'], {
            'draftId': draft_id,
            'originalDraftId': self.draft_id
        })

    def test_should_not_create_draft_with_invalid_data(self):
        res = self.client.post(
            '/draft-services/1000/copy',
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert_equal(res.status_code, 404)

    def test_should_not_copy_draft_service_description(self):
        res = self.client.post(
            '/draft-services/{}/copy'.format(self.draft_id),
            data=json.dumps({"updated_by": "me"}),
            content_type="application/json")
        data = json.loads(res.get_data())

        assert_equal(res.status_code, 201)
        assert_false("serviceSummary" in data['services'])

    def test_should_not_copy_draft_documents(self):
        res = self.client.post(
            '/draft-services/{}/copy'.format(self.draft_id),
            data=json.dumps({"updated_by": "me"}),
            content_type="application/json")
        data = json.loads(res.get_data())

        assert_equal(res.status_code, 201)
        assert_false("termsAndConditionsDocumentURL" in data['services'])
        assert_false("pricingDocumentURL" in data['services'])
        assert_false("serviceDefinitionDocumentURL" in data['services'])
        assert_false("sfiaRateDocumentURL" in data['services'])


class TestCompleteDraft(BaseApplicationTest, JSONUpdateTestMixin):
    endpoint = '/draft-services/{self.draft_id}/complete'
    method = 'post'
    draft_id = 0

    def setup(self):
        super(TestCompleteDraft, self).setup()

        with self.app.app_context():
            db.session.add(Supplier(code=1, name="Supplier 1",
                                    addresses=[Address(address_line="{} Dummy Street 1",
                                                       suburb="Dummy",
                                                       state="ZZZ",
                                                       postal_code="0000",
                                                       country='Australia')])
                           )

            Framework.query.filter_by(slug='g-cloud-7').update(dict(status='open'))
            db.session.commit()
        draft_json = self.load_example_listing("G7-SCS")
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
            '/draft-services/%s/complete' % self.draft_id,
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert_equal(res.status_code, 200, res.get_data())
        assert_equal(data['services']['status'], 'submitted')

    def test_complete_draft_should_create_audit_event(self):
        res = self.client.post(
            '/draft-services/%s/complete' % self.draft_id,
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert_equal(res.status_code, 200)

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())
        assert_equal(len(data['auditEvents']), 2)
        assert_equal(data['auditEvents'][1]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][1]['type'], 'complete_draft_service')
        assert_equal(data['auditEvents'][1]['data'], {
            'draftId': self.draft_id,
        })

    def test_should_not_complete_draft_without_updated_by(self):
        res = self.client.post(
            '/draft-services/%s/complete' % self.draft_id,
            data=json.dumps({}),
            content_type='application/json')

        assert_equal(res.status_code, 400)

    def test_should_not_complete_invalid_draft(self):
        create_draft_json = {
            'updated_by': 'joeblogs',
            'services': {
                'frameworkSlug': 'g-cloud-7',
                'lot': 'scs',
                'supplierCode': 1,
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
            '/draft-services/%s/complete' % draft['id'],
            data=json.dumps({'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert_equal(res.status_code, 400)
        errors = json.loads(res.get_data())['error']
        assert_in('serviceSummary', errors)


class TestDOSServices(BaseApplicationTest):
    updater_json = None
    create_draft_json = None

    def setup(self):
        super(TestDOSServices, self).setup()

        payload = self.load_example_listing("DOS-digital-specialist")
        self.updater_json = {
            'updated_by': 'joeblogs'
        }
        self.create_draft_json = self.updater_json.copy()
        self.create_draft_json['services'] = payload
        self.create_draft_json['services']['frameworkSlug'] = 'digital-outcomes-and-specialists'

        with self.app.app_context():
            self.set_framework_status('digital-outcomes-and-specialists', 'open')

            db.session.add(
                Supplier(code=1, name="Supplier 1",
                         addresses=[Address(address_line="{} Dummy Street 1",
                                            suburb="Dummy",
                                            state="ZZZ",
                                            postal_code="0000",
                                            country='Australia')])
            )
            db.session.commit()

    def _post_dos_draft(self, draft_json=None):

        res = self.client.post(
            '/draft-services',
            data=json.dumps(draft_json or self.create_draft_json),
            content_type='application/json')
        assert_equal(res.status_code, 201, res.get_data())
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
        assert_equal(data['services']['frameworkSlug'], 'digital-outcomes-and-specialists')
        assert_equal(data['services']['frameworkName'], 'Digital Outcomes and Specialists')
        assert_equal(data['services']['status'], 'not-submitted')
        assert_equal(data['services']['supplierCode'], 1)
        assert_equal(data['services']['lot'], 'digital-specialists')

    def test_disallow_multiple_drafts_for_one_service_lots(self):

        self._post_dos_draft()

        res = self.client.post(
            '/draft-services',
            data=json.dumps(self.create_draft_json),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert_equal(res.status_code, 400)
        assert_equal(data['error'], "'digital-specialists' service already exists for supplier '1'")

    def test_create_dos_draft_should_create_audit_event(self):

        res = self._post_dos_draft()

        data = json.loads(res.get_data())
        draft_id = data['services']['id']

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())
        assert_equal(len(data['auditEvents']), 1)
        assert_equal(data['auditEvents'][0]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][0]['type'], 'create_draft_service')
        assert_equal(
            data['auditEvents'][0]['data']['draftId'], draft_id
        )

    def test_should_fetch_a_dos_draft(self):

        res = self._post_dos_draft()
        draft_id = json.loads(res.get_data())['services']['id']
        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        assert_equal(fetch.status_code, 200)
        data = json.loads(res.get_data())
        assert_equal(data['services']['dataProtocols'], True)
        assert_equal(data['services']['id'], draft_id)

    def test_should_delete_a_dos_draft(self):

        res = self._post_dos_draft()
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

        assert_equal(len(data['auditEvents']), 2)
        assert_equal(data['auditEvents'][0]['type'], 'create_draft_service')
        assert_equal(data['auditEvents'][1]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][1]['type'], 'delete_draft_service')
        assert_equal(
            data['auditEvents'][1]['data']['draftId'], draft_id
        )

        fetch_again = self.client.get(
            '/draft-services/{}'.format(draft_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert_equal(fetch_again.status_code, 404)

    def test_should_edit_dos_draft(self):

        res = self._post_dos_draft()
        draft_id = json.loads(res.get_data())['services']['id']
        update = self._edit_dos_draft(
            draft_id=draft_id,
            services={'dataProtocols': False}
        )
        assert_equal(update.status_code, 200)

        fetch = self.client.get('/draft-services/{}'.format(draft_id))
        assert_equal(fetch.status_code, 200)
        data = json.loads(fetch.get_data())
        assert_equal(data['services']['dataProtocols'], False)
        assert_equal(data['services']['id'], draft_id)

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
            assert_equal(data['error'][key], 'not_money_format')
        assert_equal(update.status_code, 400)

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
        assert_equal(data['error']['agileCoachPriceMax'], 'max_less_than_min')
        assert_equal(update.status_code, 400)

    def test_should_not_edit_draft_if_dependencies_missing(self):

        res = self._post_dos_draft()
        draft_id = json.loads(res.get_data())['services']['id']
        update = self._edit_dos_draft(
            draft_id=draft_id,
            services={
                # missing "developerLocations"
                "dataProtocols": True,
                "developerPriceMin": "1"},
            page_questions=[]
        )
        data = json.loads(update.get_data())
        for key in ['developerLocations', 'developerPriceMax']:
            assert_equal(data['error'][key], 'answer_required')
        assert_equal(update.status_code, 400)

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
        assert_equal(update.status_code, 200)

    def test_should_not_copy_one_service_limit_lot_draft(self):

        draft = json.loads(self._post_dos_draft().get_data())

        res = self.client.post(
            '/draft-services/{}/copy'.format(draft['services']['id']),
            data=json.dumps({"updated_by": "me"}),
            content_type="application/json")
        data = json.loads(res.get_data())

        assert_equal(res.status_code, 400)
        assert_in("Cannot copy a 'digital-specialists' draft", data['error'])

    def test_complete_valid_dos_draft(self):

        res = self._post_dos_draft()
        draft_id = json.loads(res.get_data())['services']['id']
        complete = self.client.post(
            '/draft-services/{}/complete'.format(draft_id),
            data=json.dumps(self.updater_json),
            content_type='application/json'
        )
        assert_equal(complete.status_code, 200)

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
        assert_in("specialist_required", "{}".format(data['error']['_form']))
        assert_equal(complete.status_code, 400)


class TestUpdateDraftStatus(BaseApplicationTest, JSONUpdateTestMixin):
    endpoint = '/draft-services/{self.draft_id}/update-status'
    method = 'post'
    draft_id = 0

    def setup(self):
        super(TestUpdateDraftStatus, self).setup()

        with self.app.app_context():
            db.session.add(Supplier(code=1, name="Supplier 1",
                                    addresses=[Address(address_line="{} Dummy Street 1",
                                                       suburb="Dummy",
                                                       state="ZZZ",
                                                       postal_code="0000",
                                                       country='Australia')])
                           )

            Framework.query.filter_by(slug='g-cloud-7').update(dict(status='open'))
            db.session.commit()
        draft_json = self.load_example_listing("G7-SCS")
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
            '/draft-services/%s/update-status' % self.draft_id,
            data=json.dumps({'services': {'status': 'failed'}, 'updated_by': 'joeblogs'}),
            content_type='application/json')

        data = json.loads(res.get_data())
        assert_equal(res.status_code, 200, res.get_data())
        assert_equal(data['services']['status'], 'failed')

    def test_update_draft_status_should_create_audit_event(self):
        res = self.client.post(
            '/draft-services/%s/update-status' % self.draft_id,
            data=json.dumps({'services': {'status': 'failed'}, 'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert_equal(res.status_code, 200)

        audit_response = self.client.get('/audit-events')
        assert_equal(audit_response.status_code, 200)
        data = json.loads(audit_response.get_data())
        assert_equal(len(data['auditEvents']), 2)
        assert_equal(data['auditEvents'][1]['user'], 'joeblogs')
        assert_equal(data['auditEvents'][1]['type'], 'update_draft_service_status')
        assert_equal(data['auditEvents'][1]['data'], {
            'draftId': self.draft_id, 'status': 'failed'
        })

    def test_should_not_update_draft_status_to_invalid_status(self):
        res = self.client.post(
            '/draft-services/%s/update-status' % self.draft_id,
            data=json.dumps({'services': {'status': 'INVALID-STATUS'}, 'updated_by': 'joeblogs'}),
            content_type='application/json')

        assert_equal(res.status_code, 400)
        assert_equal(json.loads(res.get_data()), {"error": "'INVALID-STATUS' is not a valid status"})
