from app.api.helpers import Service
from app.models import AuditEvent
from enum import Enum
import rollbar


class AuditService(Service):
    __model__ = AuditEvent

    def __init__(self, *args, **kwargs):
        super(AuditService, self).__init__(*args, **kwargs)

    def log_audit_event(self, audit, extra_data):
        try:
            self.save(audit)
        except Exception:
            rollbar.report_exc_info(extra_data=extra_data)


class AuditTypes(Enum):
    update_price = 'update_price'
    update_brief_response = 'update_brief_response'
    update_brief_response_contact = 'update_brief_response_contact'
