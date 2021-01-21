from app.api.services import (
    publish
)
from . import celery


@celery.task
def agency(agency, event_type, **kwargs):
    publish.agency(agency, event_type, **kwargs)


def compress_agency(agency):
    return {
        'id': agency.id,
        'name': agency.name,
        'category': agency.category,
        'state': agency.state,
        'whitelisted': agency.whitelisted,
        'domains': ', '.join([d.domain for d in agency.domains])
    }


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
def brief_question(brief_question, event_type, **kwargs):
    publish.brief_question(brief_question, event_type, **kwargs)


def compress_brief_question(brief_question):
    return {
        'id': brief_question.id,
        'question': brief_question.data.get('question'),
        'created_by': brief_question.data.get('created_by'),
        'brief_id': brief_question.brief_id,
        'supplier_code': brief_question.supplier_code,
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
def mailchimp(event_type, **kwargs):
    publish.mailchimp(event_type, **kwargs)


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
def team(team, event_type, **kwargs):
    publish.team(team, event_type, **kwargs)


def compress_team(team):
    return {
        'id': team.id,
        'name': team.name,
        'email_address': team.email_address,
        'status': team.status
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
