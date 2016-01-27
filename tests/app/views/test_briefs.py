import json

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
