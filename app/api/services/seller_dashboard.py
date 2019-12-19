from datetime import datetime, timedelta

import pendulum
import pytz
from sqlalchemy import and_, case, func, literal, or_, select, union
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import joinedload, noload, raiseload

from app import db
from app.api.helpers import Service
from app.models import (Brief, BriefResponse, CaseStudy, Domain, Framework, Lot, Supplier, SupplierDomain,
                        SupplierFramework, User)


class SellerDashboardService(object):

    def get_opportunities(self, supplier_code):
        submitted_response_count_query = (
            db
            .session
            .query(
                BriefResponse.brief_id.label("brief_id"),
                func.count(BriefResponse.brief_id).label("responseCount")
            )
            .filter(
                BriefResponse.supplier_code == supplier_code,
                BriefResponse.withdrawn_at.is_(None),
                BriefResponse.submitted_at.isnot(None)
            )
            .group_by(BriefResponse.brief_id)
            .subquery()
        )

        draft_response_count_query = (
            db
            .session
            .query(
                BriefResponse.brief_id.label("brief_id"),
                func.count(BriefResponse.brief_id).label("draftResponseCount")
            )
            .filter(
                BriefResponse.supplier_code == supplier_code,
                BriefResponse.withdrawn_at.is_(None),
                BriefResponse.submitted_at.is_(None)
            )
            .group_by(BriefResponse.brief_id)
            .subquery()
        )

        brief_response_id_query = (
            db
            .session
            .query(
                BriefResponse.brief_id.label("brief_id"),
                func.max(BriefResponse.id).label("briefResponseId")
            )
            .filter(
                BriefResponse.supplier_code == supplier_code,
                BriefResponse.withdrawn_at.is_(None)
            )
            .group_by(BriefResponse.brief_id)
            .subquery()
        )

        responses_query = (
            db
            .session
            .query(
                BriefResponse.brief_id.label("brief_id")
            )
            .filter(
                BriefResponse.supplier_code == supplier_code,
                BriefResponse.withdrawn_at.is_(None)
            )
        )

        invited_query = (
            db
            .session
            .query(
                Brief.id.label("brief_id")
            )
            .filter(Brief.data['sellers']['{}'.format(supplier_code)].isnot(None))
        )

        query = union(responses_query, invited_query).alias('to_show_briefs')

        brief_query = (
            db
            .session
            .query(
                query.c.brief_id.label('briefId'),
                Brief.data['title'].astext.label('name'),
                Brief.data['numberOfSuppliers'].astext.label('numberOfSuppliers'),
                Brief.closed_at,
                Brief.withdrawn_at,
                Lot.slug.label('lot'),
                submitted_response_count_query.c.responseCount,
                draft_response_count_query.c.draftResponseCount,
                brief_response_id_query.c.briefResponseId
            )
            .join(Brief, query.c.brief_id == Brief.id)
            .join(Lot)
            .outerjoin(submitted_response_count_query, submitted_response_count_query.c.brief_id == Brief.id)
            .outerjoin(draft_response_count_query, draft_response_count_query.c.brief_id == Brief.id)
            .outerjoin(brief_response_id_query, brief_response_id_query.c.brief_id == Brief.id)
            .filter(
                Brief.published_at.isnot(None)
            )
            .subquery()
        )

        today = datetime.now(pytz.timezone('Australia/Sydney'))
        open_brief_result = (
            db
            .session
            .query(
                brief_query
            )
            .join(Brief, brief_query.c.briefId == Brief.id)
            .filter(
                Brief.closed_at >= today
            )
            .order_by(Brief.closed_at)
            .all()
        )
        closed_brief_result = (
            db
            .session
            .query(
                brief_query
            )
            .join(Brief, brief_query.c.briefId == Brief.id)
            .filter(
                Brief.closed_at < today,
                Brief.closed_at >= today - timedelta(days=60)
            )
            .order_by(Brief.closed_at.desc())
            .all()
        )

        return (
            [r._asdict() for r in open_brief_result] +
            [r._asdict() for r in closed_brief_result]
        )

    def get_team_members(self, supplier_code):
        user_type = (
            case(
                whens=[(
                    and_(
                        Supplier.data['email'].isnot(None),
                        Supplier.data['email'].astext == User.email_address
                    ), literal('ar')
                )],
                else_=literal('member')
            ).label('type')
        )

        results = (
            db
            .session
            .query(
                User.name,
                User.email_address.label('email'),
                User.id,
                user_type
            )
            .outerjoin(
                Supplier,
                Supplier.code == supplier_code
            )
            .filter(
                User.active.is_(True),
                User.supplier_code == supplier_code
            )
            .order_by(user_type, func.lower(User.name))
        )

        return [r._asdict() for r in results]
