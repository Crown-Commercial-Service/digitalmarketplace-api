from datetime import datetime, timedelta

import pytz
from sqlalchemy import and_, case, func, literal, or_, select, union
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import joinedload, noload, raiseload

from app import db
from app.api.helpers import Service
from app.models import (CaseStudy, Domain, Framework, Supplier, SupplierDomain,
                        SupplierFramework, User)


class SellerDashboardService(object):

    def get_team_members(self, supplier_code):
        user_type = (
            case(
                whens=[(Supplier.data['email'].isnot(None), literal('ar'))]
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
