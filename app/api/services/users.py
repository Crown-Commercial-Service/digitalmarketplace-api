from sqlalchemy import and_, desc, func, literal
from sqlalchemy.sql.expression import case, select
from sqlalchemy.orm import joinedload, raiseload
from app import db
from app.api.helpers import Service, abort
from app.models import Supplier, Team, TeamMember, User


class UsersService(Service):
    __model__ = User

    def __init__(self, *args, **kwargs):
        super(UsersService, self).__init__(*args, **kwargs)

    def get_user_organisation(self, email_domain):
        """Returns the user's organisation based on their email domain."""
        query = db.session.execute("""SELECT name FROM govdomains WHERE domain = :domain""",
                                   {'domain': email_domain})
        results = list(query)

        try:
            name = results[0].name
        except IndexError:
            name = 'Unknown'

        return name

    def get_team_members(self, current_user_id, email_domain, keywords=None, exclude=None):
        exclude = exclude if exclude else []
        user = (
            db
            .session
            .query(
                User.id,
                User.supplier_code,
                User.role
            )
            .filter(User.id == current_user_id)
            .one_or_none()
        )

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
                and_(
                    Supplier.data['email'].astext == User.email_address,
                    Supplier.code == User.supplier_code
                )
            )
            .filter(
                User.id != user.id,
                User.active.is_(True),
                User.email_address.like('%@{}'.format(email_domain))
            )
            .filter(User.id.notin_(exclude))
        )

        if keywords:
            results = results.filter(User.name.ilike('%{}%'.format(keywords.encode('utf-8'))))

        results = results.filter(
            User.supplier_code == user.supplier_code,
            User.role == user.role
        )

        results = results.order_by(user_type, func.lower(User.name))
        return [r._asdict() for r in results]

    def get_supplier_last_login(self, application_id):
        user_by_application_query = (db.session.query(User.supplier_code)
                                     .filter(User.application_id == application_id))

        user_by_supplier_query = (db.session.query(User)
                                  .filter(User.supplier_code.in_(user_by_application_query))
                                  .order_by(desc(User.logged_in_at)))

        return user_by_supplier_query.first()

    def get_sellers_by_email(self, emails):
        return (db.session
                  .query(User)
                  .filter(User.email_address.in_(emails))
                  .filter(User.active)
                  .filter(User.role == 'supplier')
                  .all())

    def get_by_email(self, email):
        return self.find(email_address=email).one_or_none()

    def get_buyer_team_members(self, email_domain):
        completed_teams = (db.session
                             .query(TeamMember.user_id, Team.name)
                             .join(Team)
                             .filter(Team.status == 'completed')
                             .subquery('completed_teams'))

        results = (db.session
                     .query(User.id,
                            User.name,
                            User.email_address.label('emailAddress'),
                            completed_teams.columns.name.label('teamName'))
                     .join(completed_teams, completed_teams.columns.user_id == User.id, isouter=True)
                     .filter(User.active.is_(True),
                             User.email_address.like('%@{}'.format(email_domain)),
                             User.role == 'buyer')
                     .order_by(func.lower(User.name))
                     .all())

        return [r._asdict() for r in results]

    def get_by_id(self, user_id):
        query = (
            self.find(id=user_id)
            .options(
                raiseload('*')
            )
        )
        return query.one_or_none()
