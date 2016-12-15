import sys
from contextlib import contextmanager
from app.jiraapi import get_api, get_api_oauth
from app import create_app
from app.models import Application
from pprint import pprint

app = create_app('development')


@contextmanager
def jira_with_app_context():
    with app.app_context():
        j = get_api_oauth()
        yield j


def create_assessment_task(application_id):
    with jira_with_app_context() as j:
        a = Application.query.filter_by(id=application_id).first()
        j.create_assessment_task(a)


def list_assessment_tasks():
    with jira_with_app_context() as j:
        assessment_tasks = j.get_assessment_tasks()

        for t in assessment_tasks:
            pprint(t.raw)


if __name__ == '__main__':
    try:
        task_method = getattr(sys.modules[__name__], sys.argv[1])
    except AttributeError:
        print('no such task')
    task_method(*sys.argv[2:])
