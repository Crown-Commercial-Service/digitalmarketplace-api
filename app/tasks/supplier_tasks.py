from app.api.services import (
    key_values_service,
    suppliers
)
from . import celery


@celery.task
def update_supplier_metrics():
    supplier_metrics = suppliers.get_metrics()
    key_values_service.upsert('supplier_metrics', {
        "total": supplier_metrics.get('supplier_count', 0)
    })
