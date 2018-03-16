from app.api.helpers import Service
from app import db
from app.models import User
from sqlalchemy import func
from sqlalchemy.sql.functions import concat


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

    def get_team_members(self, current_user_id, email_domain):
        """Returns a list of the user's team members."""
        team_ids = db.session.query(User.id).filter(User.id != current_user_id,
                                                    User.email_address.endswith(concat('@', email_domain)))

        results = (db.session.query(User.name, User.email_address.label('email'))
                   .filter(User.id != current_user_id, User.id.in_(team_ids), User.active.is_(True))
                   .order_by(func.lower(User.name)))

        return [r._asdict() for r in results]
