from app.api.helpers import Service
from app.models import AuditEvent
from enum import Enum
import rollbar


class AuditService(Service):
    __model__ = AuditEvent

    def __init__(self, *args, **kwargs):
        super(AuditService, self).__init__(*args, **kwargs)

    def log_audit_event(self, **kwargs):
        try:
            audit = AuditEvent(
                audit_type=kwargs['audit_type'],
                user=kwargs['user'],
                data=kwargs['data'],
                db_object=kwargs['db_object']
            )
            self.save(audit)
        except Exception:
            rollbar.report_exc_info(extra_data={
                "audit_type": kwargs['audit_type'],
                "id": kwargs['db_object'].id
            })


class AuditTypes(Enum):
    update_price = 'update_price'
    sent_closed_brief_email = 'sent_closed_brief_email'
    update_brief_response = 'update_brief_response'
    update_brief_response_contact = 'update_brief_response_contact'
