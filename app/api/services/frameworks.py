from app.api.helpers import Service
from app.models import Framework


class FrameworksService(Service):
    __model__ = Framework

    def __init__(self, *args, **kwargs):
        super(FrameworksService, self).__init__(*args, **kwargs)
