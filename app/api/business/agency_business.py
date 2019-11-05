import pendulum

from app.api.business.errors import NotFoundError
from app.api.services import agency_service, audit_service, audit_types
from app.models import AgencyDomain


def get_agencies():
    return agency_service.get_agencies()


def get_agency(agency_id):
    return agency_service.get_agency(agency_id)


def update(agency_id, agency, updated_by):
    existing = agency_service.get_agency_for_update(agency_id)

    if agency.get('name'):
        existing.name = agency.get('name')

    if agency.get('category'):
        existing.category = agency.get('category')

    if agency.get('bodyType'):
        existing.body_type = agency.get('bodyType')

    if agency.get('whitelisted', None) is not None:
        existing.whitelisted = agency.get('whitelisted')

    if agency.get('reports', None) is not None:
        existing.reports = agency.get('reports')

    if agency.get('state'):
        existing.state = agency.get('state')

    if agency.get('domains', None) is not None:
        domains = agency.get('domains', [])
        to_remove = []
        to_add = []
        for e in existing.domains:
            if e.domain not in domains:
                to_remove.append(e)

        for d in domains:
            if d not in [e.domain for e in existing.domains]:
                to_add.append(AgencyDomain(active=True, domain=d))

        for e in to_remove:
            existing.domains.remove(e)
        for e in to_add:
            existing.domains.append(e)

    updated = agency_service.save(existing)
    result = get_agency(updated.id)
    audit_service.log_audit_event(
        audit_type=audit_types.agency_updated,
        user=updated_by,
        data={
            'incoming': agency,
            'saved': result
        },
        db_object=updated)
    return result
