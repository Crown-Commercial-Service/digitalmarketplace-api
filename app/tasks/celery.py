from __future__ import absolute_import, unicode_literals
from celery import Celery
from urllib import quote_plus
from os import getenv
from kombu.transport import SQS
from flask import current_app


region = getenv('AWS_SQS_REGION')
queue_account = getenv('AWS_SQS_ACCOUNT_ID')
queue_name = getenv('AWS_SQS_QUEUE_NAME')


# we need to patch the kombu SQS transport so ListQueues isn't
# being performed on the AWS SQS API while our PR remains open.
# see: https://github.com/celery/kombu/pull/834
def monkey_patch(self, queue_name_prefix):
    self._queue_cache[queue_name] = 'https://%s.queue.amazonaws.com/%s/%s' % (region, queue_account, queue_name)
SQS.Channel._update_queue_cache = monkey_patch


def make_celery(flask_app):
    CELERY_OPTIONS = {
        'broker_transport_options': {
            'region': region
        },
        'task_default_queue': queue_name
    }
    broker = 'sqs://'
    if getenv('AWS_SQS_ACCESS_KEY_ID') and getenv('AWS_SQS_SECRET_ACCESS_KEY'):
        broker += '{}:{}@'.format(
            quote_plus(getenv('AWS_SQS_ACCESS_KEY_ID')),
            quote_plus(getenv('AWS_SQS_SECRET_ACCESS_KEY'))
        )
    celery = Celery(
        flask_app.import_name,
        broker=broker,
        include=[
            'app.tasks.email',
            'app.tasks.mailchimp',
            'app.tasks.brief_tasks'
        ]
    )
    celery.conf.update(flask_app.config)
    celery.config_from_object(CELERY_OPTIONS)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            if current_app:
                return TaskBase.__call__(self, *args, **kwargs)
            else:
                with flask_app.app_context():
                    return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery
