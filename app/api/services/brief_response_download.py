from app.api.helpers import Service
from app.models import BriefResponseDownload, User, db


class BriefResponseDownloadService(Service):
    __model__ = BriefResponseDownload

    def __init__(self, *args, **kwargs):
        super(BriefResponseDownloadService, self).__init__(*args, **kwargs)

    def get_responses_downloaded(self, brief_id):
        result = (
            db
            .session
            .query(
                BriefResponseDownload.created_at,
                User.name
            )
            .join(User)
            .filter(BriefResponseDownload.brief_id == brief_id)
            .filter(User.role != 'admin')
            .order_by(BriefResponseDownload.created_at.desc())
            .all()
        )
        return [r._asdict() for r in result]
