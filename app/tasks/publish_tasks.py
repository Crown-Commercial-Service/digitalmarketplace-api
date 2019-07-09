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


def compress_assessment(assessment):
    return {
        'id': assessment.id,
        'active': assessment.active,
        'supplier_domain_id': assessment.supplier_domain_id
    }


@celery.task
def brief(brief, event_type, **kwargs):
    publish.brief(brief, event_type, **kwargs)


def compress_brief(brief):
    return {
        'id': brief.id,
        'title': brief.data.get('title'),
        'organisation': brief.data.get('organisation'),
        'lotName': brief.lot.name
    }


@celery.task
def brief_response(brief_response, event_type, **kwargs):
    publish.brief_response(brief_response, event_type, **kwargs)


def compress_brief_response(brief_response):
    return {
        'id': brief_response.id,
        'supplier_code': brief_response.supplier_code,
        'brief_id': brief_response.brief_id
    }


@celery.task
def supplier(supplier, event_type, **kwargs):
    publish.supplier(supplier, event_type, **kwargs)


def compress_supplier(supplier):
    return {
        'id': supplier.id,
        'code': supplier.code,
        'name': supplier.name,
        'status': supplier.status
    }


@celery.task
def evidence(evidence, event_type, **kwargs):
    publish.evidence(evidence, event_type, **kwargs)


def compress_evidence(evidence):
    return {
        'id': evidence.id,
        'domainId': evidence.domain_id,
        'briefId': evidence.brief_id,
        'status': evidence.status,
        'supplierCode': evidence.supplier_code,
        'created_at': evidence.created_at,
        'updated_at': evidence.updated_at,
        'submitted_at': evidence.submitted_at
    }


@celery.task
def supplier_domain(supplier_domain, event_type, **kwargs):
    publish.supplier_domain(supplier_domain, event_type, **kwargs)


def compress_supplier_domain(supplier_domain):
    return {
        'id': supplier_domain.id,
        'domain_id': supplier_domain.domain_id,
        'status': supplier_domain.status,
        'supplier_id': supplier_domain.supplier_id,
        'price_status': supplier_domain.price_status
    }


@celery.task
def user(user, event_type, **kwargs):
    publish.user(user, event_type, **kwargs)


def compress_user(user):
    return {
        'id': user.id,
        'name': user.name,
        'email_address': user.email_address,
        'role': user.role
    }


@celery.task
def user_claim(user_claim, event_type, **kwargs):
    publish.user_claim(user_claim, event_type, **kwargs)


def compress_user_claim(user_claim):
    return {
        'id': user_claim.id,
        'email_address': user_claim.email_address,
        'claimed': user_claim.claimed
    }
