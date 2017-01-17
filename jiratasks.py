import sys
from contextlib import contextmanager
from app.jiraapi import get_marketplace_jira
from app import create_app
from app.models import Application
from pprint import pprint as p

app = create_app('development')


@contextmanager
def jira_with_app_context():
    with app.app_context():
        j = get_marketplace_jira()
        yield j


def create_assessment_task(application_id):
    with jira_with_app_context() as j:
        a = Application.query.filter_by(id=application_id).first()
        j.create_assessment_task(a)


def list_assessment_tasks():
    with jira_with_app_context() as j:
        assessment_tasks = j.get_assessment_tasks()

        for t in assessment_tasks:
            p(t.raw)


def list_assessment_tasks_with_subtasks():
    with jira_with_app_context() as j:
        p(j.assessment_tasks_by_supplier_id())


def create_subtask_issuetype():
    with jira_with_app_context() as j:
        j.create_issuetype(
            'Supplier Assessment Step',
            'A necessary step for carrying out a supplier assessment',
            subtask=True)


def connect():
    with jira_with_app_context() as j:
        p(j)


if __name__ == '__main__':
    try:
        task_method = getattr(sys.modules[__name__], sys.argv[1])
    except AttributeError:
        print('no such task')
    task_method(*sys.argv[2:])
