from app.api.helpers import Service
from app.models import AuditEvent
from enum import Enum


class AuditService(Service):
    __model__ = AuditEvent


class AuditTypes(Enum):
    update_price = 'update_price'
