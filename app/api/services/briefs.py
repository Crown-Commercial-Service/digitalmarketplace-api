from app.api.helpers import Service
from app import db
from app.models import Brief, BriefResponse


class BriefsService(Service):
    __model__ = Brief

    def __init__(self, *args, **kwargs):
        super(BriefsService, self).__init__(*args, **kwargs)

    def get_supplier_responses(self, code):
        responses = db.session.query(BriefResponse.created_at,
                                     Brief.id, Brief.data['title'].astext.label('name'),
                                     Brief.closed_at)\
            .join(Brief)\
            .filter(BriefResponse.supplier_code == code)\
            .order_by(Brief.closed_at)\
            .all()

        return [r._asdict() for r in responses]
