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
        return self.filter(Domain.name.notin_(self.legacy_domains)).all()

    def get_by_name_or_id(self, name_or_id):
        if isinstance(name_or_id, string_types):
            domain = self.filter(
                func.lower(Domain.name) == func.lower(name_or_id)
            ).one_or_none()
        else:
            domain = self.get(name_or_id)

        return domain
