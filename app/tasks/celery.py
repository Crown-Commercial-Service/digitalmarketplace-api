from __future__ import absolute_import, unicode_literals
from celery import Celery
from urllib import quote_plus
from os import getenv
from kombu.transport import SQS
from flask import current_app
from app import db


QUEUE_NAME = getenv('AWS_SQS_QUEUE_NAME')
QUEUE_URL = getenv('AWS_SQS_QUEUE_URL')  # remove when monkey_patch is removed


# we need to patch the kombu SQS transport so ListQueues isn't
# being performed on the AWS SQS API while our PR remains open.
# see: https://github.com/celery/kombu/pull/834
def monkey_patch(self, queue_name_prefix):
    self._queue_cache[QUEUE_NAME] = QUEUE_URL


SQS.Channel._update_queue_cache = monkey_patch


def make_celery(flask_app):
    region = getenv('AWS_SQS_REGION')
    celery_options = {
        'broker_transport_options': {
            'region': region
        },
        'task_default_queue': QUEUE_NAME
    }
    broker_url = getenv('AWS_SQS_BROKER_URL')
    if not broker_url:
        broker_url = 'sqs://'
        if getenv('AWS_SQS_ACCESS_KEY_ID') and getenv('AWS_SQS_SECRET_ACCESS_KEY'):
            broker_url += '{}:{}@'.format(
                quote_plus(getenv('AWS_SQS_ACCESS_KEY_ID')),
                quote_plus(getenv('AWS_SQS_SECRET_ACCESS_KEY'))
            )

    celery = Celery(
        flask_app.import_name,
        broker=broker_url,
        include=[
            'app.api.services',
            'app.emails',
            'app.emails.util',
            'app.tasks.email',
            'app.tasks.mailchimp',
            'app.tasks.brief_tasks',
            'app.tasks.s3',
            'app.tasks.brief_response_tasks',
            'app.tasks.supplier_tasks',
            'app.tasks.jira',
            'app.tasks.dreamail'
        ]
    )
    celery.conf.update(flask_app.config)
    celery.config_from_object(celery_options)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def after_return(self, *args, **kwargs):
            db.session.remove()

        def __call__(self, *args, **kwargs):
            if current_app:
                return TaskBase.__call__(self, *args, **kwargs)
            else:
                with flask_app.app_context():
                    return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery
