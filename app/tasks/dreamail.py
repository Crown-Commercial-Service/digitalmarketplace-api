from app.api.services import (
    key_values_service,
    suppliers
)
from app.emails import (
    dreamail
)
from . import celery


@celery.task
def send_dreamail(simulate, skip_audit_check):
    return dreamail.send_dreamail(simulate, skip_audit_check)
