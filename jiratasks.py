import re
import sys
from contextlib import contextmanager
from pprint import pprint as p

from app import create_app
from app.jiraapi import get_marketplace_jira
from app.models import Application

app = create_app('development')


@contextmanager
def jira_with_app_context():
    with app.app_context():
        j = get_marketplace_jira(False)
        yield j


def fix_custom_fields():
    with jira_with_app_context() as j:
        bad_issues = j.generic_jira.jira.search_issues('project = MARADMIN AND issuetype = "Supplier Assessment" '
                                                       'AND created >= 2012-05-31 AND created <= 2017-05-23')
        for bad_issue in bad_issues:
            if bad_issue.raw['fields'][j.supplier_field_code] != 0:
                bad_issue.update({j.application_field_code: str(bad_issue.raw['fields'][j.supplier_field_code]),
                                 j.supplier_field_code: str(0)})

        bad_issues = j.generic_jira.jira.search_issues('project = MARADMIN AND issuetype = "Domain Assessment" '
                                                       'AND created >= 2012-05-31 AND created <= 2017-05-23')
        for bad_issue in bad_issues:
            if bad_issue.raw['fields'][j.application_field_code] != 0:
                bad_issue.update({j.supplier_field_code:
                                 str(re.search(r"\(#(.*)\)$", bad_issue.fields.summary).group(1)),
                                 j.application_field_code: str(0)})


def create_approval_task(application_id):
    with jira_with_app_context() as j:
        a = Application.query.filter_by(id=application_id).first()
        a.status = 'submitted'
        a.create_approval_task()


def list_tasks():
    with jira_with_app_context() as j:
        assessment_tasks = j.get_assessment_tasks()

        for t in assessment_tasks:
            p(t)


def tasks_by_id():
    with jira_with_app_context() as j:
        p(j.assessment_tasks_by_application_id())


def create_subtask_issuetype():
    with jira_with_app_context() as j:
        j.create_issuetype(
            'Supplier Assessment Step',
            'A necessary step for carrying out a supplier assessment',
            subtask=True)


def connect():
    with jira_with_app_context() as j:
        si = j.generic_jira.jira.server_info()
        p(si)


if __name__ == '__main__':
    try:
        task_method = getattr(sys.modules[__name__], sys.argv[1])

    except AttributeError:
        print('no such task')
        sys.exit(1)

    task_method(*sys.argv[2:])
