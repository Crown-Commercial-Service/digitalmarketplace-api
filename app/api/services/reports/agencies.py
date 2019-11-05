from app.api.helpers import Service
from app.models import Agency, AgencyDomain
from app import db
from sqlalchemy import func


class AgenciesService(Service):
    __model__ = Agency

    def __init__(self, *args, **kwargs):
        super(AgenciesService, self).__init__(*args, **kwargs)

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
