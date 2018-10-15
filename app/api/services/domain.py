from app.api.helpers import Service
from app.models import Domain
from six import string_types
from sqlalchemy import func


class DomainService(Service):
    __model__ = Domain

    def __init__(self, *args, **kwargs):
        super(DomainService, self).__init__(*args, **kwargs)

    def get_by_name_or_id(self, name_or_id):
        if isinstance(name_or_id, string_types):
            domain = self.filter(
                func.lower(Domain.name) == func.lower(name_or_id)
            ).one_or_none()
        else:
            domain = self.get(name_or_id).one_or_none()

        return domain
