from app.api.helpers import Service
from app.models import Agency, AgencyDomain, db
from sqlalchemy import func
from sqlalchemy.orm import joinedload


class AgencyService(Service):
    __model__ = Agency

    def __init__(self, *args, **kwargs):
        super(AgencyService, self).__init__(*args, **kwargs)

    def get_agency_for_update(self, agency_id):
        return (
            db
            .session
            .query(Agency)
            .options(
                joinedload(Agency.domains)
            )
            .filter(Agency.id == agency_id)
            .one_or_none()
        )

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
                body_type='other',
                reports=True,
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

    def get_agencies(self):
        subquery = (
            db
            .session
            .query(
                AgencyDomain.agency_id,
                func.json_agg(
                    func.json_build_object(
                        'id', AgencyDomain.id,
                        'domain', AgencyDomain.domain,
                        'active', AgencyDomain.active
                    )
                ).label('domains')
            )
            .group_by(AgencyDomain.agency_id)
            .subquery()
        )

        result = (
            db
            .session
            .query(
                Agency.id,
                Agency.name,
                Agency.domain,
                Agency.category,
                Agency.state,
                Agency.body_type,
                Agency.whitelisted,
                Agency.reports,
                subquery.c.domains
            )
            .join(subquery, subquery.c.agency_id == Agency.id)
            .order_by(Agency.name)
            .all()
        )
        return [r._asdict() for r in result]

    def get_agency(self, agency_id):
        subquery = (
            db
            .session
            .query(
                AgencyDomain.agency_id,
                func.json_agg(
                    func.json_build_object(
                        'id', AgencyDomain.id,
                        'domain', AgencyDomain.domain,
                        'active', AgencyDomain.active
                    )
                ).label('domains')
            )
            .group_by(AgencyDomain.agency_id)
            .subquery()
        )

        result = (
            db
            .session
            .query(
                Agency.id,
                Agency.name,
                Agency.domain,
                Agency.category,
                Agency.state,
                Agency.body_type,
                Agency.whitelisted,
                Agency.reports,
                subquery.c.domains
            )
            .join(subquery, subquery.c.agency_id == Agency.id)
            .filter(Agency.id == agency_id)
            .one_or_none()
        )
        return result._asdict()
