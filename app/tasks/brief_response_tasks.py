from app.api.services import (
    brief_responses_service,
    key_values_service
)
from . import celery


@celery.task
def update_brief_response_metrics():
    brief_response_metrics = brief_responses_service.get_metrics()
    key_values_service.upsert('brief_response_metrics', {
        "total": brief_response_metrics.get('brief_response_count', 0)
    })
