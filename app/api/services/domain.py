from app.api.helpers import Service
from app.models import Domain
from app import db
from six import string_types
from sqlalchemy import func


class DomainService(Service):
    __model__ = Domain
    legacy_domains = ['Change, Training and Transformation']

    def __init__(self, *args, **kwargs):
        super(DomainService, self).__init__(*args, **kwargs)

    def get_active_domains(self):
        query = self.filter(Domain.name.notin_(self.legacy_domains)).order_by(Domain.name.asc())
        return query.all()

    def get_by_name_or_id(self, name_or_id, show_legacy=True):
        if isinstance(name_or_id, string_types):
            query = self.filter(
                func.lower(Domain.name) == func.lower(name_or_id)
            )
            if not show_legacy:
                query = query.filter(Domain.name.notin_(self.legacy_domains))
            domain = query.one_or_none()
        else:
            query = self.filter(Domain.id == name_or_id)
            if not show_legacy:
                query = query.filter(Domain.name.notin_(self.legacy_domains))
            domain = query.one_or_none()

        return domain
