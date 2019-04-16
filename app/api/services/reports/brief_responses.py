from app.api.helpers import Service
from app.models import BriefResponse, Brief, Lot
from app import db


class BriefResponsesService(Service):
    __model__ = BriefResponse

    def __init__(self, *args, **kwargs):
        super(BriefResponsesService, self).__init__(*args, **kwargs)

    def get_submitted_brief_responses(self):
        result = (
            db
            .session
            .query(
                BriefResponse.brief_id,
                BriefResponse.supplier_code,
                BriefResponse.created_at,
                BriefResponse.data['dayRate'].astext.label('day_rate'),
                Lot.name.label('brief_type'),
                Brief.data['areaOfExpertise'].astext.label('brief_category')
            )
            .join(Brief, Lot)
            .filter(BriefResponse.withdrawn_at.is_(None))
            .order_by(Brief.id)
            .all()
        )

        return [r._asdict() for r in result]
