from app.api.services import (
    key_values_service,
    suppliers
)
from app.emails import (
    dreamail
)
from . import celery


@celery.task
def send_dreamail():
    dreamail.send_dreamail()
