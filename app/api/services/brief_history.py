from sqlalchemy import func

from app.api.helpers import Service
from app.models import BriefHistory, db


class BriefHistoryService(Service):
    __model__ = BriefHistory

    def __init__(self, *args, **kwargs):
        super(BriefHistoryService, self).__init__(*args, **kwargs)

    def get_edits(self, brief_id):
        return (db.session
                  .query(BriefHistory)
                  .filter(BriefHistory.brief_id == brief_id)
                  .order_by(BriefHistory.edited_at.desc())
                  .all())

    def get_last_edited_date(self, brief_id):
        return (db.session
                  .query(func.max(BriefHistory.edited_at))
                  .filter(BriefHistory.brief_id == brief_id)
                  .scalar())
