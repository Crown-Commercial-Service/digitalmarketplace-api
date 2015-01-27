from flask import json
from nose.tools import assert_equal, assert_in, assert_is_none

from app import db
from app.models import Service
from datetime import datetime
from .helpers import BaseApplicationTest, JSONUpdateTestMixin


class TestListServices(BaseApplicationTest):
    def test_list_services_with_no_services(self):
        response = self.client.get('/services')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(data['services'], [])

    def test_list_services(self):
        self.setup_dummy_services(1)
        response = self.client.get('/services')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 1)

    def test_paginated_list_services_page_one(self):
        self.setup_dummy_services(15)

        response = self.client.get('/services')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 10)
        next_link = first_by_rel('next', data['links'])
        assert_in("page=2", next_link['href'])

    def test_paginated_list_services_page_two(self):
        self.setup_dummy_services(15)

        response = self.client.get('/services?page=2')
        data = json.loads(response.get_data())

        assert_equal(response.status_code, 200)
        assert_equal(len(data['services']), 5)
        prev_link = first_by_rel('prev', data['links'])
        assert_in("page=1", prev_link['href'])

    def test_paginated_list_services_page_out_of_range(self):
        self.setup_dummy_services(15)

        response = self.client.get('/services?page=10')

        # TODO: decide whether this is actually correct.
        #       this is what Flask-SQLAlchemy does by default so is easy
        assert_equal(response.status_code, 404)


def first_by_rel(rel, links):
    for link in links:
        if link['rel'] == rel:
            return link


class TestPostService(BaseApplicationTest):
    method = "post"
    endpoint = "/services"

    def test_post_is_not_supported(self):
        payload = self.load_example_listing("SSP-JSON-IaaS")
        response = self.client.post(
            "/services",
            data=json.dumps({'services': payload}),
            content_type='application/json')

        assert_equal(response.status_code, 501)


class TestPutService(BaseApplicationTest, JSONUpdateTestMixin):
    method = "put"
    endpoint = "/services/2"

    def setup(self):
        super(TestPutService, self).setup()
        now = datetime.now()
        with self.app.app_context():
            db.session.add(Service(service_id=2,
                                   supplier_id=321,
                                   updated_at=now,
                                   created_at=now,
                                   data={'foo': 'bar'}))

    def test_update_a_service(self):
        payload = self.load_example_listing("SSP-JSON-IaaS")
        response = self.client.put(
            '/services/2',
            data=json.dumps({'services': payload}),
            content_type='application/json')

        assert_equal(response.status_code, 204)

    def test_add_a_new_service(self):
        payload = self.load_example_listing("SSP-JSON-IaaS")
        payload['id'] = 3
        response = self.client.put(
            '/services/3',
            data=json.dumps({'services': payload}),
            content_type='application/json')

        assert_equal(response.status_code, 201)

    def test_when_service_payload_has_invalid_id(self):
        response = self.client.put(
            '/services/2',
            data=json.dumps({'services': {'id': 3, 'foo': 'bar'}}),
            content_type='application/json')

        assert_equal(response.status_code, 400)


class TestGetService(BaseApplicationTest):
    def test_get_non_existent_service(self):
        response = self.client.get('/services/123')
        assert_equal(404, response.status_code)

    def test_get_service(self):
        now = datetime.now()
        with self.app.app_context():
            db.session.add(Service(service_id=123,
                                   supplier_id=321,
                                   updated_at=now,
                                   created_at=now,
                                   data={'foo': 'bar'}))
        response = self.client.get('/services/123')

        data = json.loads(response.get_data())
        assert_equal(200, response.status_code)
        assert_equal(123, data['services']['id'])
