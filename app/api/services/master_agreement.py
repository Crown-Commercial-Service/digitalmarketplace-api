from app.api.helpers import Service
from app.models import MasterAgreement


class MasterAgreementService(Service):
    __model__ = MasterAgreement

    def __init__(self, *args, **kwargs):
        super(MasterAgreementService, self).__init__(*args, **kwargs)
