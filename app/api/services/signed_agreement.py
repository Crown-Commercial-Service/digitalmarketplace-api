from app.api.helpers import Service
from app.models import SignedAgreement


class SignedAgreementService(Service):
    __model__ = SignedAgreement

    def __init__(self, *args, **kwargs):
        super(SignedAgreementService, self).__init__(*args, **kwargs)
