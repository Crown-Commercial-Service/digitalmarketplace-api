from app.api.helpers import Service
from app import db
from app.models import Brief, BriefResponse, BriefUser, AuditEvent, Framework, Lot, User, WorkOrder
from sqlalchemy import and_, case, func, or_
from sqlalchemy.sql.expression import case as sql_case
from sqlalchemy.sql.functions import concat
from sqlalchemy.types import Numeric
import pendulum


class BriefsService(Service):
    __model__ = Brief

    def __init__(self, *args, **kwargs):
        super(BriefsService, self).__init__(*args, **kwargs)

    def get_supplier_responses(self, code):
        responses = db.session.query(BriefResponse.created_at.label('response_date'),
                                     Brief.id, Brief.data['title'].astext.label('name'),
                                     Lot.name.label('framework'),
                                     Brief.closed_at,
                                     case([(AuditEvent.type == 'read_brief_responses', True)], else_=False)
                                     .label('is_downloaded'))\
            .distinct(Brief.closed_at, Brief.id)\
            .join(Brief, Lot)\
            .outerjoin(AuditEvent, and_(Brief.id == AuditEvent.data['briefId'].astext.cast(Numeric),
                                        AuditEvent.type == 'read_brief_responses'))\
            .filter(BriefResponse.supplier_code == code,
                    Brief.closed_at > pendulum.create(2018, 1, 1),
                    BriefResponse.withdrawn_at.is_(None)
                    )\
            .order_by(Brief.closed_at, Brief.id)\
            .all()

        return [r._asdict() for r in responses]

    def get_user_briefs(self, current_user_id):
        """Returns summary of a user's briefs with the total number of sellers that applied."""
        results = (db.session.query(Brief.id, Brief.data['title'].astext.label('name'),
                                    Brief.closed_at, Brief.status, func.count(BriefResponse.id).label('applications'),
                                    Framework.slug.label('framework'), Lot.slug.label('lot'),
                                    WorkOrder.id.label('work_order'))
                   .join(BriefUser, Framework, Lot)
                   .filter(current_user_id == BriefUser.user_id)
                   .outerjoin(BriefResponse, Brief.id == BriefResponse.brief_id)
                   .outerjoin(WorkOrder)
                   .group_by(Brief.id, Framework.slug, Lot.slug, WorkOrder.id)
                   .order_by(sql_case([
                       (Brief.status == 'draft', 1),
                       (Brief.status == 'live', 2),
                       (Brief.status == 'closed', 3)]), Brief.closed_at.desc().nullslast())
                   .all())

        return [r._asdict() for r in results]

    def get_team_briefs(self, current_user_id, domain):
        """Returns summary of live and closed briefs submitted by the user's team."""
        team_ids = db.session.query(User.id).filter(User.id != current_user_id,
                                                    User.email_address.endswith(concat('@', domain)))

        team_brief_ids = db.session.query(BriefUser.brief_id).filter(BriefUser.user_id.in_(team_ids))

        results = (db.session.query(Brief.id, Brief.data['title'].astext.label('name'), Brief.closed_at, Brief.status,
                                    Framework.slug.label('framework'), Lot.slug.label('lot'), User.name.label('author'))
                   .join(BriefUser, Framework, Lot, User)
                   .filter(Brief.id.in_(team_brief_ids), or_(Brief.status == 'live', Brief.status == 'closed'))
                   .order_by(sql_case([
                       (Brief.status == 'live', 1),
                       (Brief.status == 'closed', 2)]), Brief.closed_at.desc().nullslast())
                   .all())

        return [r._asdict() for r in results]
