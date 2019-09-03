from app.api.services import (
    agency_service,
    audit_service,
    audit_types,
    briefs,
    domain_service,
    frameworks_service,
    lots_service,
    users
)


def create(current_user):
    lot = lots_service.find(slug='training2').one_or_none()
    framework = frameworks_service.find(slug='digital-marketplace').one_or_none()
    user = users.get(current_user.id)
    agency_name = ''

    email_domain = user.email_address.split('@')[1]
    agency = agency_service.find(domain=email_domain).one_or_none()
    if agency:
        agency_name = agency.name

    domain = domain_service.find(name='Training, Learning and Development').one_or_none()
    seller_category = None
    if domain:
        seller_category = str(domain.id)
    else:
        raise Exception('Training, Learning and Development domain not found')

    brief = briefs.create_brief(user, current_user.get_team(), framework, lot, data={
        'organisation': agency_name,
        'sellerCategory': seller_category
    })

    audit_service.log_audit_event(
        audit_type=audit_types.create_brief,
        user=current_user.email_address,
        data={
            'briefId': brief.id
        },
        db_object=brief)

    return brief
