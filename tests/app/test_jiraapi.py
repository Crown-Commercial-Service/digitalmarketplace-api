from __future__ import unicode_literals

import mock
from flask import current_app
from app.jiraapi import get_api, get_api_oauth, JIRAAPI

from .helpers import BaseApplicationTest
from app.models import Application, User


class TestJira(BaseApplicationTest):
    @mock.patch('app.jiraapi.JIRA')
    def test_basic_jira(self, jira):
        with self.app.app_context():
            get_api()
            jira.assert_called_with(
                current_app.config['JIRA_URL'],
                basic_auth=['a', 'b']
            )

    @mock.patch('app.jiraapi.JIRA')
    def test_oauth_jira(self, jira):
        with self.app.app_context():
            get_api_oauth()
            jira.assert_called_with(
                current_app.config['JIRA_URL'],
                oauth={
                    'access_token': 'at',
                    'consumer_key': 'ck',
                    'access_token_secret': 'ats',
                    'key_cert': 'kc'
                }
            )

    @mock.patch('app.jiraapi.JIRA')
    @mock.patch('app.jiraapi.get_api_oauth')
    @mock.patch('app.jiraapi.get_api')
    @mock.patch('app.jiraapi.JIRAAPI')
    def test_create_assessment_task(self, JIRAAPI, get_api, get_api_oauth, JIRA):
        with self.app.app_context():
            j = JIRAAPI()
            get_api_oauth.return_value = j

            u_id = self.setup_dummy_user()
            user = User.query.get(u_id)

            x = Application(
                id=99,
                status='submitted',
                data={'name': 'Umbrella Corporation'},
                user=user)
            x.set_approval(True)
            j.create_assessment_task.assert_called_with(x)
