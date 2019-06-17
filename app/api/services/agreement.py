from app.api.helpers import Service
from app.models import Agreement, db


class AgreementService(Service):
    __model__ = Agreement

    def __init__(self, *args, **kwargs):
        super(AgreementService, self).__init__(*args, **kwargs)
