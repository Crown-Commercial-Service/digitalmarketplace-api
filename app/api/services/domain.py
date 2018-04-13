from app.api.helpers import Service
from app.models import Domain


class DomainService(Service):
    __model__ = Domain

    def __init__(self, *args, **kwargs):
        super(DomainService, self).__init__(*args, **kwargs)
