from app.api.helpers import Service
from app.models import Application


class ApplicationService(Service):
    __model__ = Application

    def __init__(self, *args, **kwargs):
        super(ApplicationService, self).__init__(*args, **kwargs)
