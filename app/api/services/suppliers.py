from app.api.helpers import Service
from app.models import Supplier


class SuppliersService(Service):
    __model__ = Supplier
