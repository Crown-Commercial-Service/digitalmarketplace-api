import pendulum
from sqlalchemy import and_, case, desc, func, or_, union
from sqlalchemy.orm import joinedload, noload
from sqlalchemy.sql.expression import case as sql_case
from sqlalchemy.sql.functions import concat
from sqlalchemy.types import Numeric, Integer

from app import db
from app.api.helpers import Service
from app.models import (
    AuditEvent,
    Brief,
    BriefAssessor,
    BriefClarificationQuestion,
    BriefQuestion,
    BriefResponse,
    BriefUser,
    Framework,
    Lot,
    Supplier,
    Team,
    TeamBrief,
    TeamMember,
    User,
    WorkOrder
)
from dmutils.filters import timesince


class BriefsService(Service):
    __model__ = Brief

    def __init__(self, *args, **kwargs):
        super(BriefsService, self).__init__(*args, **kwargs)

    def get_brief_counts(self, user_id):
        accessible_briefs_subquery = self.accessible_briefs(user_id)
        result = [r._asdict() for r in (
            db
            .session
            .query(
                Brief.status
            )
            .join(
                accessible_briefs_subquery,
                accessible_briefs_subquery.columns.brief_id == Brief.id
            )
            .all()
        )]
        return {
            'withdrawn': result.count({'status': 'withdrawn'}),
            'draft': result.count({'status': 'draft'}),
            'live': result.count({'status': 'live'}),
            'closed': result.count({'status': 'closed'})
        }

    def get_buyer_dashboard_briefs(self, user_id, status):
        brief_response_subquery = (
            db
            .session
            .query(
                BriefResponse.brief_id,
                func.count(BriefResponse.id).label('responses'),
            )
            .group_by(BriefResponse.brief_id)
            .subquery()
        )
        brief_question_subquery = (
            db
            .session
            .query(
                BriefQuestion.brief_id,
                func.count(BriefQuestion.id).label('questionsAsked'),
            )
            .group_by(BriefQuestion.brief_id)
            .subquery()
        )
        brief_clarification_question_subquery = (
            db
            .session
            .query(
                BriefClarificationQuestion._brief_id,
                func.count(BriefClarificationQuestion.id).label('questionsAnswered')
            )
            .group_by(BriefClarificationQuestion._brief_id)
            .subquery()
        )
        accessible_briefs_subquery = self.accessible_briefs(user_id)
        accessible_briefs_subquery = (
            db
            .session
            .query(
                accessible_briefs_subquery.columns.brief_id,
                func.array_agg(User.name).label('creators'),
            )
            .join(User, accessible_briefs_subquery.columns.user_id == User.id)
            .group_by(accessible_briefs_subquery.columns.brief_id)
            .subquery()
        )
        query = (
            db
            .session
            .query(
                Brief.id,
                Brief.data['title'].astext.label('name'),
                Brief.data['internalReference'].astext.label('internalReference'),
                Brief.data['sellers'].label('sellers'),
                Brief.data['sellerSelector'].label('sellerSelector'),
                Brief.closed_at,
                Brief.questions_closed_at,
                Brief.status,
                accessible_briefs_subquery.columns.creators,
                brief_response_subquery.columns.responses,
                brief_question_subquery.columns.questionsAsked,
                brief_clarification_question_subquery.columns.questionsAnswered,
                Lot.slug.label('lot'),
                Framework.slug.label('framework')
            )
            .join(Lot, Framework)
            .join(
                accessible_briefs_subquery,
                accessible_briefs_subquery.columns.brief_id == Brief.id
            )
        )
        if status:
            query = query.filter(Brief.status == status)
        results = (
            query
            .outerjoin(brief_response_subquery, brief_response_subquery.columns.brief_id == Brief.id)
            .outerjoin(brief_question_subquery, brief_question_subquery.columns.brief_id == Brief.id)
            .outerjoin(
                brief_clarification_question_subquery,
                brief_clarification_question_subquery.columns.brief_id == Brief.id
            )
            .order_by(sql_case([
                (Brief.status == 'draft', 1),
                (Brief.status == 'live', 2),
                (Brief.status == 'closed', 3)]),
                Brief.closed_at.desc().nullslast(),
                Brief.id.desc())
            .all()
        )

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
        brief_type_filters = [x for x in brief_type if x in ['outcomes', 'training', 'specialists', 'atm']]
        location_filters = [x for x in location if x in ['ACT', 'NSW', 'NT', 'QLD', 'SA', 'TAS', 'VIC', 'WA', 'Remote']]

        query = (db.session
                   .query(Brief.id, Brief.data['title'].astext.label('name'), Brief.closed_at,
                          Brief.data['organisation'].astext.label('company'),
                          Brief.data['location'].label('location'),
                          Brief.data['sellerSelector'].astext.label('openTo'),
                          func.count(BriefResponse.id).label('submissions'),
                          Lot.slug.label('lot'))
                   .outerjoin(
                       BriefResponse,
                       and_(Brief.id == BriefResponse.brief_id,
                            BriefResponse.withdrawn_at.is_(None),
                            BriefResponse.submitted_at.isnot(None)))
                   .outerjoin(Lot)
                   .group_by(Brief.id, Lot.id))

        lots = db.session.query(Lot).all()
        if status_filters:
            cond = or_(*[Brief.status == x for x in status_filters])
            query = query.filter(cond)

        if open_to_filters:
            switcher = {
                'all': 'allSellers',
                'selected': 'someSellers',
                'one': 'oneSeller'
            }
            atm_lot = next(iter([x for x in lots if x.slug == 'atm']))
            cond = or_(
                and_(Brief._lot_id == atm_lot.id, Brief.data['sellerSelector'].astext == 'someSellers'),
                *[Brief.data['sellerSelector'].astext == switcher.get(x) for x in open_to_filters]
            )
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
            switcher = {
                'atm': [x.id for x in lots if x.slug == 'atm'],
                'outcomes': [x.id for x in lots if x.slug in ['digital-outcome', 'rfx']],
                'training': [x.id for x in lots if x.slug in ['training', 'training2']],
                'specialists': [x.id for x in lots if x.slug in ['digital-professionals', 'specialist']]
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
            elif 'atm' in brief_type_filters:
                # this is a list of historic prod brief ids we want to show when the atm filter is active
                atm_ids = [136, 180, 207, 351, 383, 453, 485, 490, 548, 568, 633, 743, 819, 830, 862, 975, 1071,
                           1147, 1176, 1238, 1239, 1260, 1263, 1268, 1413, 1476, 1620, 1646, 1935]
                ids_cond = or_(Brief.id.in_(atm_ids))
                cond = or_(lot_cond, ids_cond)
                query = query.filter(cond)
            else:
                query = query.filter(lot_cond)

        query = (query
                 .filter(Brief.published_at.isnot(None))
                 .filter(Brief.withdrawn_at.is_(None))
                 .order_by(Brief.published_at.desc()))

        results = query.all()

        return [r._asdict() for r in results]

    def get_open_briefs_published_since(self, since=None):
        if not since:
            since = pendulum.now().subtract(hours=24)
        query = (
            db.session.query(Brief)
            .join(Framework)
            .filter(Framework.slug == 'digital-marketplace')
            .filter(
                or_(
                    Brief.data['sellerSelector'].astext == 'allSellers',
                    and_(
                        Brief.data['sellerSelector'].astext == 'someSellers',
                        Brief.data['openTo'].astext == 'category'
                    )
                )
            )
            .filter(Brief.published_at >= since)
            .filter(Brief.withdrawn_at.is_(None))
        )

        results = query.all()

        return results

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

    def create_brief(self, user, team, framework, lot, data=None):
        if not data:
            data = {}

        brief = None
        if team:
            team_brief = TeamBrief(
                team_id=team.get('id'),
                user_id=user.id
            )
            brief = Brief(
                team_briefs=[team_brief],
                framework=framework,
                lot=lot,
                data=data
            )
        else:
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

    def accessible_briefs(self, user_id):
        team_member_subquery = (
            db
            .session
            .query(
                TeamMember.team_id
            )
            .join(Team)
            .filter(TeamMember.user_id == user_id)
            .filter(Team.status == 'completed')
            .subquery()
        )
        team_member_result = (
            db
            .session
            .query(
                TeamMember.team_id,
                TeamMember.user_id
            )
            .join(team_member_subquery, team_member_subquery.columns.team_id == TeamMember.team_id)
            .all()
        )
        team_ids = [tm.team_id for tm in team_member_result]
        user_ids = [tm.user_id for tm in team_member_result]

        if team_ids:
            team_brief_query = (
                db
                .session
                .query(
                    TeamBrief.brief_id.label('brief_id'),
                    TeamBrief.user_id.label('user_id')
                )
                .join(Team)
                .filter(TeamBrief.team_id.in_(team_ids))
                .filter(Team.status == 'completed')
            )

            brief_user_query = (
                db
                .session
                .query(
                    BriefUser.brief_id.label('brief_id'),
                    BriefUser.user_id.label('user_id')
                )
                .filter(BriefUser.user_id.in_(user_ids))
            )
            query = union(team_brief_query, brief_user_query).alias('result')
            return (
                db
                .session
                .query(
                    query.c.brief_id.label('brief_id'),
                    query.c.user_id.label('user_id')
                )
                .subquery()
            )

        else:
            query = (
                db
                .session
                .query(
                    BriefUser.brief_id.label('brief_id')
                )
                .filter(BriefUser.user_id == user_id)
                .subquery()
            )
            return (
                db
                .session
                .query(
                    BriefUser.brief_id.label('brief_id'),
                    BriefUser.user_id.label('user_id')
                )
                .filter(BriefUser.brief_id.in_(query))
                .subquery()
            )

    def has_permission_to_brief(self, user_id, brief_id):
        query = self.accessible_briefs(user_id)
        result = (
            db
            .session
            .query(query)
            .filter(query.c.brief_id == brief_id)
            .all()
        )

        return True if len(result) > 0 else False

    def get_contact_for_team_brief(self, brief_id):
        team_brief = (db.session
                        .query(TeamBrief)
                        .filter(TeamBrief.brief_id == brief_id)
                        .one_or_none())

        if team_brief:
            team = (db.session
                      .query(Team)
                      .filter(Team.id == team_brief.team_id)
                      .one_or_none())

            if team and team.email_address:
                return team.email_address
            else:
                user = (db.session
                          .query(User)
                          .filter(
                              User.id == team_brief.user_id,
                              User.active.is_(True))
                          .one_or_none())

                return user.email_address

        return None

    def get_contacts_for_brief_users(self, brief_id):
        brief_users = (db.session
                         .query(BriefUser)
                         .filter(BriefUser.brief_id == brief_id)
                         .all())

        if brief_users:
            brief_user_ids = [brief_user.user_id for brief_user in brief_users]

            team_email_addresses = (db.session
                                      .query(Team.email_address)
                                      .join(TeamMember)
                                      .filter(
                                          Team.status == 'completed',
                                          TeamMember.user_id.in_(brief_user_ids))
                                      .all())

            if team_email_addresses:
                return team_email_addresses

            email_addresses = (db.session
                                 .query(User.email_address)
                                 .filter(
                                     User.id.in_(brief_user_ids),
                                     User.active.is_(True))
                                 .all())

            return email_addresses

        return None

    def get_brief_contact_details(self, brief_id):
        contact = self.get_contact_for_team_brief(brief_id)
        if contact is not None:
            return contact

        contacts = self.get_contacts_for_brief_users(brief_id)
        if contacts is not None:
            return contacts

        return None

    def get_all_user_seller_responses_within_date_range(self, current_user_id, start_date, end_date):
        subquery = self.accessible_briefs(current_user_id)
        result = (
            db
            .session
            .query(
                BriefResponse.id.label('brief_response_id'),
                BriefResponse.data['specialistGivenNames'].astext.label('specialistGivenNames'),
                BriefResponse.data['specialistSurname'].astext.label('specialistSurname'),
                BriefResponse.data['specialistName'].astext.label('specialistName'),
                BriefResponse.data['availability'].astext.label('availability'),
                BriefResponse.data['dayRate'].astext.label('dayRate'),
                BriefResponse.data['hourRate'].astext.label('hourRate'),
                BriefResponse.data['visaStatus'].astext.label('visaStatus'),
                BriefResponse.data['securityClearance'].astext.label('securityClearance'),
                BriefResponse.data['previouslyWorked'].astext.label('previouslyWorked'),
                BriefResponse.data['essentialRequirements'].label('essentialRequirements'),
                BriefResponse.data['niceToHaveRequirements'].label('niceToHaveRequirements'),
                BriefResponse.data['criteria'].label('criteria'),
                BriefResponse.data['respondToEmailAddress'].astext.label('respondToEmailAddress'),
                BriefResponse.data['respondToPhone'].astext.label('respondToPhone'),
                BriefResponse.created_at,
                Brief.id.label('brief_id'),
                Brief.data['preferredFormatForRates'].astext.label('preferredFormatForRates'),
                Brief.data['essentialRequirements'].label('essentialRequirementsCriteria'),
                Brief.data['niceToHaveRequirements'].label('niceToHaveRequirementsCriteria'),
                Lot.slug.label('slug'),
                Supplier.name.label('supplier_name'),
                Supplier.abn.label('supplier_abn')
            )
            .join(Brief, Brief.id == BriefResponse.brief_id)
            .join(Lot)
            .join(Supplier, Supplier.code == BriefResponse.supplier_code)
            .join(subquery, subquery.c.brief_id == BriefResponse.brief_id)
            .filter(Brief.created_at >= pendulum.parse(start_date, tz='Australia/Canberra'))
            .filter(Brief.created_at <= pendulum.parse(end_date, tz='Australia/Canberra'))
            .filter(Brief.published_at.isnot(None))
            .filter(BriefResponse.withdrawn_at.is_(None))
            .filter(BriefResponse.submitted_at.isnot(None))
            .filter(Lot.slug != 'training')
            .order_by(Brief.id)
        )

        return [r._asdict() for r in result.all()]

    def get_oppportunities_for_download(self, current_user_id, start_date, end_date, lot_slugs):
        subquery = self.accessible_briefs(current_user_id)
        brief_subquery = (
            db
            .session
            .query(
                Brief.id.label('brief_id'),
                func.json_object_keys(Brief.data['sellers']).label('supplier_code')
            )
            .subquery()
        )
        supplier_subquery = (
            db
            .session
            .query(
                func.json_agg(
                    func.json_build_object(
                        'abn', Supplier.abn,
                        'name', Supplier.name
                    )
                ).label('sellers'),
                brief_subquery.c.brief_id
            )
            .join(brief_subquery, brief_subquery.c.supplier_code.cast(Integer) == Supplier.code)
            .group_by(brief_subquery.c.brief_id)
            .subquery()
        )
        result = (
            db
            .session
            .query(
                Brief.id,
                Brief.data['title'].astext.label('title'),
                Brief.data['internalReference'].label('internalReference'),
                Brief.data['organisation'].astext.label('organisation'),
                Brief.data['summary'].astext.label('summary'),
                Brief.data['location'].label('location'),
                Brief.data['areaOfExpertise'].astext.label('areaOfExpertise'),
                Brief.data['openTo'].astext.label('openTo'),
                Brief.data['startDate'].astext.label('startDate'),
                Brief.data['evaluationType'].label('evaluationType'),
                Brief.data['evaluationCriteria'].label('evaluationCriteria'),
                supplier_subquery.columns.sellers.label('sellers'),
                Brief.data['essentialRequirements'].label('essentialRequirements'),
                Brief.data['niceToHaveRequirements'].label('niceToHaveRequirements'),
                Brief.created_at.label('created_at'),
                Brief.published_at.label('published_at'),
                Brief.closed_at.label('closed_at'),
                Lot.slug.label('slug'),
                User.email_address,
                Supplier.name.label('awarded_to'),
                WorkOrder.created_at.label('time_awarded'),
                Brief.data['numberOfSuppliers'].astext.label('numberOfSuppliers'),
                Brief.data['preferredFormatForRates'].astext.label('preferredFormatForRates'),
                Brief.data['maxRate'].astext.label('maxRate'),
                Brief.data['securityClearance'].astext.label('securityClearance'),
                Brief.data['contractLength'].astext.label('contractLength'),
                Brief.data['contractExtensions'].astext.label('contractExtensions'),
                Brief.data['workingArrangements'].astext.label('workingArrangements'),
                Brief.data['proposalType'].label('proposalType')
            )
            .join(Lot)
            .join(subquery, subquery.c.brief_id == Brief.id)
            .join(User, User.id == subquery.c.user_id)
            .outerjoin(WorkOrder)
            .outerjoin(Supplier, Supplier.code == WorkOrder.supplier_code)
            .outerjoin(supplier_subquery, supplier_subquery.columns.brief_id == Brief.id)
            .filter(Lot.slug.in_(lot_slugs))
            .filter(Brief.created_at >= pendulum.parse(start_date, tz='Australia/Canberra'))
            .filter(Brief.created_at <= pendulum.parse(end_date, tz='Australia/Canberra'))
            .filter(Brief.published_at.isnot(None))
            .all()
        )

        return [r._asdict() for r in result]
