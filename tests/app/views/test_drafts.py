from tests.app.helpers import BaseApplicationTest
from flask import json
from app.models import Supplier, ContactInformation
from app import db

from nose.tools import assert_equal, assert_in


class TestDraftServices(BaseApplicationTest):
    service_id = None
    updater_json = None

    def setup(self):
        super(TestDraftServices, self).setup()

        payload = self.load_example_listing("G6-IaaS")

        self.service_id = str(payload['id'])
        self.updater_json = {
            'update_details': {
                'updated_by': 'joeblogs'}
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

    def test_reject_invalid_service_id_on_update(self):
        res = self.client.post(
            '/services/invalid-id!/draft',
            data=json.dumps({'key': 'value'}),
            content_type='application/json')

        assert_equal(res.status_code, 400)

    def test_reject_update_with_no_updater_details(self):
        res = self.client.post('/services/0000000000/draft')

        assert_equal(res.status_code, 400)

    def test_reject_put_with_no_update_details(self):
        res = self.client.put('/services/0000000000/draft')

        assert_equal(res.status_code, 400)

    def test_reject_invalid_service_id_on_put(self):
        res = self.client.put(
            '/services/invalid-id!/draft',
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert_equal(res.status_code, 400)

    def test_reject_invalid_service_id_on_get(self):
        res = self.client.get('/services/invalid-id!/draft')

        assert_equal(res.status_code, 400)

    def test_reject_invalid_service_id_on_delete(self):
        res = self.client.delete(
            '/services/invalid-id!/draft',
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert_equal(res.status_code, 400)

    def test_reject_delete_with_no_update_details(self):
        res = self.client.delete('/services/0000000000/draft')

        assert_equal(res.status_code, 400)

    def test_reject_invalid_service_id_on_publish(self):
        res = self.client.post(
            '/services/invalid-id!/draft/publish',
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert_equal(res.status_code, 400)

    def test_reject_publish_with_no_update_details(self):
        res = self.client.post('/services/0000000000/draft/publish')

        assert_equal(res.status_code, 400)

    def test_should_404_if_service_does_not_exist_on_create_draft(self):
        res = self.client.put(
            '/services/0000000000/draft',
            data=json.dumps(self.updater_json),
            content_type='application/json')

        assert_equal(res.status_code, 404)

    def test_should_create_draft_from_existing_service(self):
        res = self.client.put(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        data = json.loads(res.get_data())

        assert_equal(res.status_code, 201)
        assert_equal(data['services']['service_id'], self.service_id)

    def test_should_not_create_two_drafts_from_existing_service(self):
        self.client.put(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        res = self.client.put(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        data = json.loads(res.get_data())

        assert_equal(res.status_code, 400)
        assert_in(
            'duplicate key value violates unique constraint "ix_draft_services_service_id"\nDETAIL:  Key (service_id)=(1234567890123456) already exists.',  # noqa
            data['error'])

    def test_should_fetch_a_draft(self):
        res = self.client.put(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert_equal(res.status_code, 201)

        fetch = self.client.get('/services/{}/draft'.format(self.service_id))
        assert_equal(fetch.status_code, 200)
        data = json.loads(res.get_data())
        assert_equal(data['services']['service_id'], self.service_id)

    def test_should_404_on_fetch_a_draft_that_doesnt_exist(self):
        fetch = self.client.get('/services/0000000000/draft')
        assert_equal(fetch.status_code, 404)

    def test_should_404_on_delete_a_draft_that_doesnt_exist(self):
        res = self.client.delete(
            '/services/0000000000/draft',
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert_equal(res.status_code, 404)

    def test_should_delete_a_draft(self):
        res = self.client.put(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert_equal(res.status_code, 201)
        fetch = self.client.get('/services/{}/draft'.format(self.service_id))
        assert_equal(fetch.status_code, 200)
        delete = self.client.delete(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert_equal(delete.status_code, 200)
        fetch_again = self.client.get(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')
        assert_equal(fetch_again.status_code, 404)

    def test_should_be_able_to_update_a_draft(self):
        self.client.put(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        update = self.client.post(
            '/services/{}/draft'.format(self.service_id),
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

        fetch = self.client.get('/services/{}/draft'.format(self.service_id))
        data = json.loads(fetch.get_data())
        assert_equal(fetch.status_code, 200)
        assert_equal(data['services']['serviceName'], 'new service name')

    def test_should_be_a_400_if_no_service_block_in_update(self):
        self.client.put(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        update = self.client.post(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs'}
            }),
            content_type='application/json')

        assert_equal(update.status_code, 400)

    def test_should_not_be_able_to_launch_invalid_service(self):
        self.client.put(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        self.client.post(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs'},
                'services': {
                    'badField': 'new service name',
                    'priceUnit': 'chickens'
                }
            }),
            content_type='application/json')

        res = self.client.post(
            '/services/{}/draft/publish'.format(self.service_id),
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs',
                }
            }),
            content_type='application/json')

        assert_equal(res.status_code, 400)

    def test_should_not_be_able_to_publish_a_draft_if_no_service(self):
        res = self.client.post(
            '/services/{}/draft/publish'.format(self.service_id),
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs',
                }
            }),
            content_type='application/json')
        assert_equal(res.status_code, 404)

    def test_should_be_able_to_launch_valid_service(self):
        initial = self.client.get('/services/{}'.format(self.service_id))
        assert_equal(initial.status_code, 200)
        assert_equal(
            json.loads(initial.get_data())['services']['serviceName'],
            'My Iaas Service')

        self.client.put(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps(self.updater_json),
            content_type='application/json')

        first_draft = self.client.get(
            '/services/{}/draft'.format(self.service_id))
        assert_equal(first_draft.status_code, 200)
        assert_equal(
            json.loads(first_draft.get_data())['services']['serviceName'],
            'My Iaas Service')

        self.client.post(
            '/services/{}/draft'.format(self.service_id),
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs'},
                'services': {
                    'serviceName': 'chickens'
                }
            }),
            content_type='application/json')

        updated_draft = self.client.get(
            '/services/{}/draft'.format(self.service_id))
        assert_equal(updated_draft.status_code, 200)
        assert_equal(
            json.loads(updated_draft.get_data())['services']['serviceName'],
            'chickens')

        res = self.client.post(
            '/services/{}/draft/publish'.format(self.service_id),
            data=json.dumps({
                'update_details': {
                    'updated_by': 'joeblogs',
                }
            }),
            content_type='application/json')
        assert_equal(res.status_code, 200)

        # draft should no longer exist
        fetch = self.client.get('/services/{}/draft'.format(self.service_id))
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
