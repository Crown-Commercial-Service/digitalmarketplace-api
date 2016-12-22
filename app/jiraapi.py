from __future__ import unicode_literals

import io

from jira import JIRA
from flask import current_app

import json
from functools import partial


MARKETPLACE_PROJECT = 'MAR'
ASSESSMENT_ISSUE_TYPE = 'Supplier Assessment'


TICKET_DESCRIPTION = """Please review this potential supplier to determine if they meet the requirements.

The application comprises the following information:

{}

"""


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

    def get_assessment_tasks(self):
        SEARCH = "project={} and type='{}'".format(
            MARKETPLACE_PROJECT,
            ASSESSMENT_ISSUE_TYPE)
        return self.jira.search_issues(SEARCH)

    def create_assessment_task(self, application):
        task_details = dict(
            project=MARKETPLACE_PROJECT,
            summary='Review this Supplier Application: {}'.format(application.supplier.name),
            description=TICKET_DESCRIPTION.format(application.json),
            issuetype={'name': ASSESSMENT_ISSUE_TYPE}
        )
        new_issue = self.jira.create_issue(**task_details)

    def get_issuetypes(self):
        url = self.jira._get_url('issuetype')
        response = self.s.get(url)
        return response.json()

    def create_issuetype(self, issuetype_name, description):
        url = self.jira._get_url('issuetype')

        data = {
            "name": issuetype_name,
            "description": description,
            "type": "standard"
        }

        response = self.s.post(url, data=json.dumps(data))
        return response.json()

    def ensure_issue_type_exists(self, issuetype_name, description):
        existing = self.get_issuetypes()

        names = [_['name'] for _ in existing]

        issuetype_exists = issuetype_name in set(names)

        if not issuetype_exists:
            its = self.create_issuetype(issuetype_name, description)
        else:
            its = next(_ for _ in existing if _['name'] == issuetype_name)
        return its

    def get_project(self, projectcode):
        url = self.jira._get_url('project/{}'.format(projectcode))
        resp = self.s.get(url)
        return resp.json()

    def issue_type_is_attached_to_project(self, issuetype, projectcode):
        proj = self.get_project(projectcode)
        issuetype_names = [_['name'] for _ in proj['issueTypes']]
        return issuetype in issuetype_names

    def assessment_issue_type_attached(self):
        self.issue_type_is_attached_to_project(ASSESSMENT_ISSUE_TYPE, MARKETPLACE_PROJECT)


def get_api():
    JIRA_URL = current_app.config['JIRA_URL']
    JIRA_CREDS = current_app.config['JIRA_CREDS']
    creds = JIRA_CREDS.split(':', 1)

    jira = JIRA(JIRA_URL, basic_auth=creds)
    return JIRAAPI(jira)


def get_api_oauth():
    JIRA_URL = current_app.config['JIRA_URL']
    JIRA_CREDS_OAUTH = current_app.config['JIRA_CREDS_OAUTH']

    at, ats, ck, kc = JIRA_CREDS_OAUTH.split(',', 3)

    oauth_dict = {
        'access_token': at,
        'access_token_secret': ats,
        'consumer_key': ck,
        'key_cert': kc
    }

    authed_jira = JIRA(JIRA_URL, oauth=oauth_dict)
    return JIRAAPI(authed_jira)
