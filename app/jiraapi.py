from __future__ import unicode_literals

import io
import re

from jira import JIRA
from flask import current_app

import json
from functools import partial


ASSESSMENT_ISSUE_TYPE = 'Supplier Assessment'

TICKET_DESCRIPTION = """Please review this potential supplier to determine if they meet the requirements.

The application comprises the following information:

{}

"""


def to_snake(s, sep='-'):
    s = s.replace(' ', '')
    return (s[0].lower() + re.sub(
        r'([A-Z])', lambda m: sep + m.group(0).lower(), s[1:]))


class MarketplaceJIRA(object):
    def __init__(
            self,
            generic_jira,
            marketplace_project_code=None,
            application_field_code=None,
            supplier_field_code=None):
        if not marketplace_project_code:
            marketplace_project_code = current_app.config.get('JIRA_MARKETPLACE_PROJECT_CODE')
        self.marketplace_project_code = marketplace_project_code

        if not application_field_code:
            application_field_code = current_app.config.get('JIRA_APPLICATION_FIELD_CODE')
        self.application_field_code = application_field_code

        if not supplier_field_code:
            supplier_field_code = current_app.config.get('JIRA_SUPPLIER_FIELD_CODE')
        self.supplier_field_code = supplier_field_code

        self.generic_jira = generic_jira

    @property
    def server_url(self):
        jj = self.generic_jira.jira.server_info()
        return jj['baseUrl']

    def make_link(self, key):
        return self.server_url + '/browse/' + key

    def create_supplier_domain_assessment_task(self, supplier, domains):
        if not domains:
            return
        task_details = dict(
            project=self.marketplace_project_code,
            summary='Assess "{}" for domain(s)'.format(supplier.name),
            description=TICKET_DESCRIPTION.format(supplier.json),
            issuetype={'name': ASSESSMENT_ISSUE_TYPE}
        )
        new_issue = self.generic_jira.jira.create_issue(**task_details)
        new_issue.update({self.supplier_field_code: str(supplier.id)})

        for domain in domains:
            name = domain.name
            child_issue = self.generic_jira.create_issue(
                self.marketplace_project_code,
                name,
                name,
                'Supplier Assessment Step',
                parent={'key': str(new_issue)})

    def create_application_approval_task(self, application):
        summary = 'Application assessment: {}'.format(application.data.get('name'))
        description = TICKET_DESCRIPTION.format(application.json)

        details = dict(
            project=self.marketplace_project_code,
            summary=summary,
            description=description,
            issuetype_name=ASSESSMENT_ISSUE_TYPE
        )

        new_issue = self.generic_jira.create_issue(**details)
        new_issue.update({self.application_field_code: str(application.id)})

        for label in ['Check Profile', 'Check Documents']:
            child_issue = self.generic_jira.create_issue(
                self.marketplace_project_code,
                label,
                label,
                'Supplier Assessment Step',
                parent={'key': str(new_issue)})

    def get_assessment_tasks(self):
        return self.generic_jira.issues_with_subtasks(
            self.marketplace_project_code,
            ASSESSMENT_ISSUE_TYPE
        )

    def assessment_tasks_by_application_id(self):
        assessment_issues = self.generic_jira.issues_with_subtasks(
            self.marketplace_project_code,
            ASSESSMENT_ISSUE_TYPE
        )

        def task_info(t):
            info = {
                'id': t['id'],
                'key': t['key'],
                'self': t['self'],
                'link': self.make_link(t['key']),
                'summary': t['fields']['summary'],
                'status': to_snake(t['fields']['status']['name'], '-'),
                'link': self.make_link(t['key'])
            }

            try:
                info['subtasks'] = [task_info(st) for st in t['full_subtasks']]
            except KeyError:
                pass
            return info

        return {_['fields'][self.application_field_code]: task_info(_) for _ in assessment_issues}

    def custom_fields(self):
        f = self.generic_jira.get_fields()

        return {
            x['name']: x
            for x in f
            if x['custom']
        }

    def assessment_issue_type_attached(self):
        return self.generic_jira.issue_type_is_attached_to_project(ASSESSMENT_ISSUE_TYPE, self.marketplace_project_code)


class GenericJIRA(object):
    def __init__(self, jira):
        self.jira = jira
        self.s = self.jira._session
        self.server_info = self.jira.server_info()

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

    def create_issue(self, project, summary, description, issuetype_name, **kwargs):
        details = dict(
            project=project,
            summary=summary,
            description=description,
            issuetype={'name': issuetype_name}
        )

        details.update(**kwargs)
        new_issue = self.jira.create_issue(**details)
        return new_issue

    def get_issues_of_type(self, project_code, issuetype_name):
        SEARCH = "project={} and type='{}'".format(
            project_code,
            issuetype_name)
        results = self.jira.search_issues(SEARCH)
        return results

    def issues_with_subtasks(self, project_code, issuetype_name):
        issues = self.get_issues_of_type(project_code, issuetype_name)

        def fully_populated_issue(issue):
            issue['full_subtasks'] = [
                self.get_specific_issue(subtask['id'])
                for subtask in issue['fields']['subtasks']
            ]
            return issue

        return [fully_populated_issue(_.raw) for _ in issues]

    def get_specific_issue(self, task_id):
        url = self.jira._get_url('issue/{}'.format(task_id))
        response = self.s.get(url)
        return response.json()

    def get_issue_fields(self, issue_id):
        url = self.jira._get_url('issue/{}/editmeta'.format(issue_id))
        response = self.s.get(url)
        return response.json()

    def get_issuetypes(self):
        url = self.jira._get_url('issuetype')
        response = self.s.get(url)
        return response.json()

    def get_fields(self):
        url = self.jira._get_url('field')
        response = self.s.get(url)
        return response.json()

    def create_issuetype(self, issuetype_name, description, subtask=False):
        typename = 'standard' if not subtask else 'subtask'

        url = self.jira._get_url('issuetype')

        data = {
            "name": issuetype_name,
            "description": description,
            "type": typename
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


def get_api():
    JIRA_URL = current_app.config['JIRA_URL']
    JIRA_CREDS = current_app.config['JIRA_CREDS']
    creds = JIRA_CREDS.split(':', 1)

    return JIRA(JIRA_URL, basic_auth=creds)


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

    return JIRA(JIRA_URL, oauth=oauth_dict)


def get_marketplace_jira(oauth=True):
    if oauth:
        api = get_api_oauth()
    else:
        api = get_api()

    return MarketplaceJIRA(GenericJIRA(api))
