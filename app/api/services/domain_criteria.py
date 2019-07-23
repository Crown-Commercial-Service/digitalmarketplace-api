from app.api.helpers import Service
from app.models import DomainCriteria
from app import db
from sqlalchemy.orm import raiseload


class DomainCriteriaService(Service):
    __model__ = DomainCriteria

    def __init__(self, *args, **kwargs):
        super(DomainCriteriaService, self).__init__(*args, **kwargs)

    def get_criteria_by_domain_id(self, domain_id):
        query = (
            self.filter(DomainCriteria.domain_id == domain_id)
            .options(
                raiseload('*')
            )
            .order_by(DomainCriteria.id.asc())
        )
        return query.all()
