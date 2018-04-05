from app.api.helpers import Service
from app import db
from app.models import BriefResponse, Supplier


class BriefResponsesService(Service):
    __model__ = BriefResponse

    def __init__(self, *args, **kwargs):
        super(BriefResponsesService, self).__init__(*args, **kwargs)

    def get_brief_responses(self, brief_id, supplier_code):
        responses = (db.session.query(BriefResponse.created_at,
                                      BriefResponse.id,
                                      BriefResponse.brief_id,
                                      BriefResponse.supplier_code,
                                      Supplier.name.label('supplier_name'))
                     .join(Supplier)
                     .filter(BriefResponse.supplier_code == supplier_code,
                             BriefResponse.brief_id == brief_id,
                             BriefResponse.withdrawn_at.is_(None))
                     .all())

        return [r._asdict() for r in responses]
