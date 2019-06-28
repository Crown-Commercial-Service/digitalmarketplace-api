from app import db
from app.api.helpers import Service
from app.models import WorkOrder


class WorkOrderService(Service):
    __model__ = WorkOrder

    def __init__(self, *args, **kwargs):
        super(WorkOrderService, self).__init__(*args, **kwargs)
