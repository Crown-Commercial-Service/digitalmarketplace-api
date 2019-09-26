from app.api.helpers import Service
from app.models import Agency, AgencyDomain, db


class AgencyService(Service):
    __model__ = Agency

    def __init__(self, *args, **kwargs):
        super(AgencyService, self).__init__(*args, **kwargs)

    def get_or_add_agency(self, domain):
        from app.tasks import publish_tasks
        domain = domain.lower()
        agency = self.get_agency_by_domain(domain)
        if not agency:
            agency = self.save(Agency(
                name=domain,
                domain=domain,
                category='Commonwealth',
                state='ACT',
                whitelisted=True,
                domains=[AgencyDomain(
                    domain=domain,
                    active=True
                )]
            ))

            publish_tasks.agency.delay(
                publish_tasks.compress_agency(agency),
                'created'
            )
        return agency

    def get_agency_name(self, agency_id):
        agency = self.get(agency_id)
        if agency:
            return agency.name
        return 'Unknown'

    def get_agency_by_domain(self, domain):
        result = (
            db
            .session
            .query(
                Agency.id
            )
            .join(AgencyDomain)
            .filter(AgencyDomain.domain == domain)
            .one_or_none()
        )

        return result

    def get_agency_domains(self, agency_id):
        result = (
            db
            .session
            .query(
                AgencyDomain.domain
            )
            .filter(AgencyDomain.active.is_(True))
            .filter(AgencyDomain.agency_id == agency_id)
            .order_by(AgencyDomain.domain)
            .all()
        )
        return [r.domain for r in result]
