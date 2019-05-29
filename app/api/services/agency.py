from app.api.helpers import Service
from app.models import Agency, db


class AgencyService(Service):
    __model__ = Agency

    def __init__(self, *args, **kwargs):
        super(AgencyService, self).__init__(*args, **kwargs)
