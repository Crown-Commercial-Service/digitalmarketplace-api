from sqlalchemy import func, union
from sqlalchemy.sql import text

from app import db
from app.api.helpers import Service
from app.models import Brief, BriefUser, Lot, Team, TeamBrief, User


class BriefsService(Service):
    __model__ = Brief

    def __init__(self, *args, **kwargs):
        super(BriefsService, self).__init__(*args, **kwargs)

    def get_published_briefs(self):
        team_brief_query = (
            db
            .session
            .query(
                TeamBrief.brief_id.label('brief_id'),
                func.array_agg(func.substring(User.email_address, '@(.*)')).label('domain')
            )
            .join(Team)
            .join(User)
            .filter(Team.status == 'completed')
            .group_by(TeamBrief.brief_id)
        )

        brief_user_query = (
            db
            .session
            .query(
                BriefUser.brief_id.label('brief_id'),
                func.array_agg(func.substring(User.email_address, '@(.*)')).label('domain')
            )
            .join(User)
            .group_by(BriefUser.brief_id)
        )
        subquery = union(team_brief_query, brief_user_query).alias('result')

        result = (
            db
            .session
            .query(
                Brief.id,
                Brief.data['organisation'].astext.label('organisation'),
                Brief.published_at,
                Brief.withdrawn_at,
                Brief.data['title'].astext.label('title'),
                Brief.data['sellerSelector'].astext.label('openTo'),
                Brief.data['areaOfExpertise'].astext.label('brief_category'),
                Lot.name.label('brief_type'),
                subquery.columns.domain[1].label('publisher_domain')
            )
            .join(subquery, Brief.id == subquery.columns.brief_id)
            .join(Lot)
            .filter(Brief.published_at.isnot(None))
            .order_by(Brief.id)
            .all()
        )

        return [r._asdict() for r in result]
