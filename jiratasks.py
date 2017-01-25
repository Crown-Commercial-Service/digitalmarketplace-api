import sys
from contextlib import contextmanager
from app.jiraapi import get_marketplace_jira
from app import create_app
from app.models import Application, BriefResponse
from pprint import pprint as p

app = create_app('development')


@contextmanager
def jira_with_app_context():
    with app.app_context():
        j = get_marketplace_jira()
        yield j


def create_approval_task(application_id):
    with jira_with_app_context() as j:
        a = Application.query.filter_by(id=application_id).first()
        a.status = 'submitted'
        a.create_approval_task()


def create_domain_assessments(brief_response_id):
    with jira_with_app_context() as j:
        a = BriefResponse.query.filter_by(id=brief_response_id).first()
        a.create_just_in_time_assessment_tasks()


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
        p(j)
        si = j.generic_jira.jira.server_info()
        p(si)
        p(j.base_url)


if __name__ == '__main__':
    try:
        task_method = getattr(sys.modules[__name__], sys.argv[1])

    except AttributeError:
        print('no such task')
        sys.exit(1)

    task_method(*sys.argv[2:])
