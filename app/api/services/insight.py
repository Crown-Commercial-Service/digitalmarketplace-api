import pendulum
from app.api.helpers import Service
from app.models import Insight, db


class InsightService(Service):
    __model__ = Insight

    def __init__(self, *args, **kwargs):
        super(InsightService, self).__init__(*args, **kwargs)

    def get_insight(self, now, active_only=True):
        query = (
            db
            .session
            .query(
                Insight.id,
                Insight.data
            )
        )

        if active_only:
            query = query.filter(Insight.active)

        result = None
        if now:
            result = (
                query
                .filter(Insight.published_at >= now.start_of('month'))
                .filter(Insight.published_at <= now.end_of('month'))
                .one_or_none()
            )
        else:
            result = (
                query
                .order_by(Insight.published_at.desc())
                .first()
            )

        return result._asdict() if result else None

    def get_insight_for_update(self, now):
        return (
            db
            .session
            .query(Insight)
            .filter(Insight.published_at >= now.start_of('month'))
            .filter(Insight.published_at <= now.end_of('month'))
            .one_or_none()
        )
