import json

import mock
from ..helpers import BaseApplicationTest

from app import db


class TestBriefs(BaseApplicationTest):
    def setup(self):
        super(TestBriefs, self).setup()
        self.user_id = self.setup_dummy_user(role='buyer')

    def test_create_brief_with_no_data(self):
        res = self.client.post(
            '/briefs',
            content_type='application/json')

        assert res.status_code == 400

    def test_create_brief(self):
        res = self.client.post(
            '/briefs',
            data=json.dumps({'briefs': {
                'userId': self.user_id,
                'frameworkSlug': 'g-cloud-7',
                'lot': 'iaas',
            }}),
            content_type='application/json')

        assert res.status_code == 201

    def test_create_brief_fails_if_user_does_not_exist(self):
        res = self.client.post(
            '/briefs',
            data=json.dumps({'briefs': {
                'userId': 999,
                'frameworkSlug': 'g-cloud-7',
                'lot': 'iaas',
            }}),
            content_type='application/json')

        assert res.status_code == 400
        assert json.loads(res.get_data(as_text=True))['error'] == 'User ID does not exist'

    def test_create_brief_fails_if_frmework_does_not_exist(self):
        res = self.client.post(
            '/briefs',
            data=json.dumps({'briefs': {
                'userId': self.user_id,
                'frameworkSlug': 'not-exists',
                'lot': 'iaas',
            }}),
            content_type='application/json')

        assert res.status_code == 400
        assert json.loads(res.get_data(as_text=True))['error'] == "Framework 'not-exists' does not exist"

    def test_create_brief_fails_if_lot_does_not_exist(self):
        res = self.client.post(
            '/briefs',
            data=json.dumps({'briefs': {
                'userId': self.user_id,
                'frameworkSlug': 'g-cloud-7',
                'lot': 'not-exists',
            }}),
            content_type='application/json')

        assert res.status_code == 400
        assert json.loads(res.get_data(as_text=True))['error'] == "Incorrect lot 'not-exists' for framework 'g-cloud-7'"

    def test_get_brief(self):
        self.setup_dummy_briefs(1)
        res = self.client.get('/briefs/1')

        assert res.status_code == 200
        assert json.loads(res.get_data(as_text=True)) == {
            'briefs': {
                'id': 1,
                'title': 'Brief 1',
                'frameworkSlug': 'g-cloud-6',
                'frameworkName': 'G-Cloud 6',
                'frameworkStatus': 'live',
                'lot': 'saas',
                'lotName': 'Software as a Service',
                'createdAt': mock.ANY,
                'updatedAt': mock.ANY,
                'links': {
                    'framework': 'http://localhost/frameworks/g-cloud-6',
                    'self': 'http://localhost/briefs/1',
                },
            }
        }

    def test_get_brief_returns_404_if_not_exists(self):
        res = self.client.get('/briefs/1')

        assert res.status_code == 404

    def test_list_briefs(self):
        self.setup_dummy_briefs(3)

        res = self.client.get('/briefs')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == 3

    def test_list_briefs_pagination_page_one(self):
        self.setup_dummy_briefs(7)

        res = self.client.get('/briefs')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        assert len(data['briefs']) == 5
        assert data['links']['next'] == 'http://localhost/briefs?page=2'
        assert data['links']['last'] == 'http://localhost/briefs?page=2'

    def test_list_briefs_pagination_page_two(self):
        self.setup_dummy_briefs(7)

        res = self.client.get('/briefs?page=2')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        assert len(data['briefs']) == 2
        assert data['links']['prev'] == 'http://localhost/briefs?page=1'
