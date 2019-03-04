from app.api.services import (
    publish
)
from . import celery


@celery.task
def application(application, event_type, **kwargs):
    publish.application(application, event_type, **kwargs)


def compress_application(application):
    return {
        'id': application.id,
        'name': application.data.get('name'),
        'status': application.status,
        'type': application.type,
        'supplier_code': application.supplier_code
    }


@celery.task
def assessment(assessment, event_type, **kwargs):
    publish.assessment(assessment, event_type, **kwargs)


@celery.task
def brief(brief, event_type, **kwargs):
    publish.brief(brief, event_type, **kwargs)


@celery.task
def brief_response(brief_response, event_type, **kwargs):
    publish.brief_response(brief_response, event_type, **kwargs)


@celery.task
def supplier(supplier, event_type, **kwargs):
    publish.supplier(supplier, event_type, **kwargs)


@celery.task
def supplier_domain(supplier_domain, event_type, **kwargs):
    publish.supplier_domain(supplier_domain, event_type, **kwargs)


@celery.task
def user(user, event_type, **kwargs):
    publish.user(user, event_type, **kwargs)


@celery.task
def user_claim(user_claim, event_type, **kwargs):
    publish.user_claim(user_claim, event_type, **kwargs)
