from jira import JIRA
from flask import current_app

import json
from functools import partial


MARKETPLACE_PROJECT = 'MAR'


class JIRAAPI(object):
    def __init__(self, jira):
        self.jira = jira
        self.s = self.jira._session

    def http(self, method, resource, url=None, data=None):
        method = getattr(self.s, method)

        if not url:
            url = self.jira._get_url(resource)

        params = dict(url=url)
        if data:
            params['data'] = data

        resp = method(**params)
        return json.loads(resp.text, indent=4)

    def __getattr__(self, name):
        return partial(self.http, name)

    def create_assessment_task(self, application_id, issuetype):
        task_details = dict(
            project=MARKETPLACE_PROJECT,
            summary='Review this Seller Application: {}'.format(application_id),
            description='Please review this seller to determine if they meet the requirements',
            issuetype={'name': issuetype}
        )
        new_issue = self.jira.create_issue(**task_details)

    def create_issue_type(self, issuetype_name, description):
        url = self.jira._get_url('issuetype')

        data = {
            "name": issuetype_name,
            "description": description,
            "type": "standard"
        }

        self.s.post(url, data=json.dumps(data))


def get_api():
    JIRA_URL = current_app.config['JIRA_URL']
    JIRA_CREDS = current_app.config['JIRA_CREDS']
    creds = JIRA_CREDS.split(':', 1)

    jira = JIRA(JIRA_URL, basic_auth=creds)
    return JIRAAPI(jira)
