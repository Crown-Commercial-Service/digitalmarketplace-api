from tests.app.helpers import BaseApplicationTest
from flask import json
from app.models import Supplier, ContactInformation
from app import db

from nose.tools import assert_equal


class TestDraftServices(BaseApplicationTest):

    service_id = None

    def setup(self):
        super(TestDraftServices, self).setup()

        payload = self.load_example_listing("G6-IaaS")

        self.service_id = str(payload['id'])
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
                    'updated_by': 'joeblogs',
                    'update_reason': 'whateves'},
                 'services': payload}),
            content_type='application/json')

    def test_reject_invalid_service_id_on_post(self):
        res = self.client.post(
            '/services/invalid-id!/draft',
            data=json.dumps({'key': 'value'}),
            content_type='application/json')

        assert_equal(res.status_code, 400)

    def test_reject_invalid_service_id_on_put(self):
        res = self.client.put('/services/invalid-id!/draft')

        assert_equal(res.status_code, 400)

    def test_reject_invalid_service_id_on_get(self):
        res = self.client.get('/services/invalid-id!/draft')

        assert_equal(res.status_code, 400)

    def test_reject_invalid_service_id_on_delete(self):
        res = self.client.delete('/services/invalid-id!/draft')

        assert_equal(res.status_code, 400)

    def test_reject_invalid_service_id_on_publish(self):
        res = self.client.post('/services/invalid-id!/draft/publish')

        assert_equal(res.status_code, 400)

    def test_should_404_if_service_does_not_exist_on_create_draft(self):
        res = self.client.put('/services/does-not-exist/draft')

        assert_equal(res.status_code, 404)

    def test_should_create_draft_from_existing_service(self):
        res = self.client.put('/services/{}/draft'.format(self.service_id))
        data = json.loads(res.get_data())

        assert_equal(res.status_code, 201)
        assert_equal(data['services']['service_id'], self.service_id)

    def test_should_not_create_two_drafts_from_existing_service(self):
        self.client.put('/services/{}/draft'.format(self.service_id))
        res = self.client.put('/services/{}/draft'.format(self.service_id))
        data = json.loads(res.get_data())

        assert_equal(res.status_code, 400)
        assert_equal(data['error'], 'duplicate key value violates unique constraint "ix_draft_services_service_id"\nDETAIL:  Key (service_id)=(1234567890123456) already exists.\n')  # noqa

    def test_should_fetch_a_draft(self):
        res = self.client.put('/services/{}/draft'.format(self.service_id))
        assert_equal(res.status_code, 201)

        fetch = self.client.get('/services/{}/draft'.format(self.service_id))
        assert_equal(fetch.status_code, 200)
        data = json.loads(res.get_data())
        assert_equal(data['services']['service_id'], self.service_id)

    def test_should_404_on_fetch_a_draft_that_doesnt_exist(self):
        fetch = self.client.get('/services/0000000000/draft')
        assert_equal(fetch.status_code, 404)

    def test_should_404_on_delete_a_draft_that_doesnt_exist(self):
        res = self.client.delete('/services/0000000000/draft')
        assert_equal(res.status_code, 404)

    def test_should_delete_a_draft(self):
        res = self.client.put('/services/{}/draft'.format(self.service_id))
        assert_equal(res.status_code, 201)
        fetch = self.client.get('/services/{}/draft'.format(self.service_id))
        assert_equal(fetch.status_code, 200)
        delete = self.client.delete(
            '/services/{}/draft'.format(self.service_id))
        assert_equal(delete.status_code, 200)
        fetch_again = self.client.get(
            '/services/{}/draft'.format(self.service_id))
        assert_equal(fetch_again.status_code, 404)
