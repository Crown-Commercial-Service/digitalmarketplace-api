from sqlalchemy import and_, case, func, or_, desc
from sqlalchemy.sql.expression import case as sql_case
from sqlalchemy.sql.functions import concat
from sqlalchemy.types import Numeric
import pendulum
from app.api.helpers import Service
from app import db
from app.models import Brief, BriefResponse, BriefUser, AuditEvent, Framework, Lot, User, WorkOrder, BriefAssessor
from dmutils.filters import timesince


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
                       (Brief.status == 'closed', 3)]), Brief.closed_at.desc().nullslast(), Brief.id.desc())
                   .all())

        return [r._asdict() for r in results]

    def get_team_briefs(self, current_user_id, domain):
        """Returns summary of live and closed briefs submitted by the user's team."""
        team_ids = db.session.query(User.id).filter(User.id != current_user_id,
                                                    User.email_address.endswith(concat('@', domain)))

        team_brief_ids = db.session.query(BriefUser.brief_id).filter(BriefUser.user_id.in_(team_ids))

        results = (db.session.query(Brief.id, Brief.data['title'].astext.label('name'), Brief.closed_at, Brief.status,
                                    Framework.slug.label('framework'), Lot.slug.label('lot'), User.name.label('author'),
                                    func.count(BriefResponse.id).label('applications'))
                   .join(BriefUser, Framework, Lot, User)
                   .filter(Brief.id.in_(team_brief_ids), or_(Brief.status == 'live', Brief.status == 'closed'))
                   .outerjoin(BriefResponse, Brief.id == BriefResponse.brief_id)
                   .group_by(Brief.id, Framework.slug, Lot.slug, User.name)
                   .order_by(sql_case([
                       (Brief.status == 'live', 1),
                       (Brief.status == 'closed', 2)]), Brief.closed_at.desc().nullslast(), Brief.id.desc())
                   .all())

        return [r._asdict() for r in results]

    def get_assessors(self, brief_id):
        results = (db.session.query(BriefAssessor.id, BriefAssessor.brief_id, BriefAssessor.email_address,
                                    User.email_address.label('user_email_address'))
                   .outerjoin(User)
                   .filter(BriefAssessor.brief_id == brief_id)
                   .all())

        return [r._asdict() for r in results]

    def get_briefs_by_filters(self, status=None, open_to=None, brief_type=None, location=None):
        status = status or []
        open_to = open_to or []
        brief_type = brief_type or []
        location = location or []
        status_filters = [x for x in status if x in ['live', 'closed']]
        open_to_filters = [x for x in open_to if x in ['all', 'selected', 'one']]
        brief_type_filters = [x for x in brief_type if x in ['outcomes', 'training', 'specialists']]
        location_filters = [x for x in location if x in ['ACT', 'NSW', 'NT', 'QLD', 'SA', 'TAS', 'VIC', 'WA', 'Remote']]

        query = (db.session
                   .query(Brief.id, Brief.data['title'].astext.label('name'), Brief.closed_at,
                          Brief.data['organisation'].astext.label('company'),
                          Brief.data['location'].label('location'),
                          Brief.data['sellerSelector'].astext.label('openTo'),
                          func.count(BriefResponse.id).label('submissions'),
                          Lot.slug.label('lot'))
                   .outerjoin(BriefResponse, Brief.id == BriefResponse.brief_id)
                   .outerjoin(Lot)
                   .group_by(Brief.id, Lot.id))

        if status_filters:
            cond = or_(*[Brief.status == x for x in status_filters])
            query = query.filter(cond)

        if open_to_filters:
            switcher = {
                'all': 'allSellers',
                'selected': 'someSellers',
                'one': 'oneSeller'
            }
            cond = or_(*[Brief.data['sellerSelector'].astext == switcher.get(x) for x in open_to_filters])
            query = query.filter(cond)

        if location_filters:
            switcher = {
                'ACT': 'Australian Capital Territory',
                'NSW': 'New South Wales',
                'NT': 'Northern Territory',
                'QLD': 'Queensland',
                'SA': 'South Australia',
                'TAS': 'Tasmania',
                'VIC': 'Victoria',
                'WA': 'Western Australia',
                'Remote': 'Offsite'
            }
            cond = or_(*[Brief.data['location'].astext.contains(switcher.get(x)) for x in location_filters])
            query = query.filter(cond)

        if brief_type_filters:
            lots = db.session.query(Lot).all()
            switcher = {
                'outcomes': [x.id for x in lots if x.slug in ['digital-outcome', 'rfx']],
                'training': [x.id for x in lots if x.slug == 'training'],
                'specialists': [x.id for x in lots if x.slug == 'digital-professionals']
            }
            lot_cond = or_(*[Brief._lot_id.in_(switcher.get(x)) for x in brief_type_filters])

            if 'training' in brief_type_filters:
                # this is a list of historic prod brief ids we want to show when the training filter is active
                training_ids = [105, 183, 205, 215, 217, 292, 313, 336, 358, 438, 477, 498, 535, 577, 593, 762,
                                864, 868, 886, 907, 933, 1029, 1136, 1164, 1310, 1443]
                ids_cond = or_(Brief.id.in_(training_ids))

                # we also want specialist briefs with a area of expertise of 'Training, Learning and Development'
                aoe_cond = or_(Brief.data['areaOfExpertise'].astext == 'Training, Learning and Development')

                cond = or_(lot_cond, ids_cond, aoe_cond)
                query = query.filter(cond)
            else:
                query = query.filter(lot_cond)

        query = (query
                 .filter(Brief.published_at.isnot(None))
                 .filter(Brief.withdrawn_at.is_(None))
                 .order_by(Brief.published_at.desc()))

        results = query.all()

        return [r._asdict() for r in results]

    def get_metrics(self):
        brief_query = (
            db
            .session
            .query(
                Brief.id,
                Brief.published_at
            )
            .filter(
                Brief.withdrawn_at.is_(None),
                Brief.published_at.isnot(None)
            )
        )
        most_recent_brief = (
            brief_query
            .order_by(
                desc(
                    Brief.published_at
                )
            )
            .first()
        )

        return {
            'total': brief_query.count(),
            'live': brief_query.filter(Brief.closed_at.isnot(None), Brief.closed_at > pendulum.now()).count(),
            'open_to_all': brief_query.filter(Brief.data['sellerSelector'].astext == 'allSellers').count(),
            'open_to_selected': brief_query.filter(Brief.data['sellerSelector'].astext == 'someSellers').count(),
            'open_to_one': brief_query.filter(Brief.data['sellerSelector'].astext == 'oneSellers').count(),
            'recent_brief_time_since': (timesince(most_recent_brief.published_at)) if most_recent_brief else ''
        }

    def create_brief(self, user, framework, lot, data=None):
        if not data:
            data = {}
        brief = Brief(
            users=[user],
            framework=framework,
            lot=lot,
            data=data
        )
        db.session.add(brief)
        db.session.commit()
        return brief

    def save_brief(self, brief):
        db.session.add(brief)
        db.session.commit()
        return brief
