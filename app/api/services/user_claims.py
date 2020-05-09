from datetime import datetime
from app.api.helpers import Service
from app import db
from app.api.helpers import generate_random_token
from app.models import UserClaim


class UserClaimService(Service):
    __model__ = UserClaim

    def __init__(self, *args, **kwargs):
        super(UserClaimService, self).__init__(*args, **kwargs)

    def get_active_claims(self, email_address=None, type=None, team_id=None):
        query = db.session.query(UserClaim).filter(UserClaim.claimed.is_(False))
        if email_address:
            query = query.filter(UserClaim.email_address == email_address)
        if type:
            query = query.filter(UserClaim.type == type)
        if team_id:
            query = query.filter(UserClaim.data['team_id'].astext == str(team_id))
        return query.all()

    # records a claim of ownership of a user email address
    def make_claim(self, type=None, email_address=None, data=None):
        if not data:
            data = {}
        saved = False
        if email_address and data:
            token = generate_random_token()
            claim = UserClaim(type=type, token=token, email_address=email_address, data=data)
            self.save(claim)
            saved = True
        return claim if saved else None

    def get_claim(self, token=None, type=None, email_address=None, claimed=False):
        query = (
            db.session.query(UserClaim)
            .filter(UserClaim.token == token, UserClaim.type == type)
            .filter(UserClaim.claimed.is_(claimed))
        )
        if email_address:
            query = query.filter(UserClaim.email_address == email_address)
        return query.first()

    # attempts to validate the claim and records the claim as claimed if successful
    def validate_and_update_claim(self, type=None, token=None, email_address=None, age=None):
        claimed = False
        if token and email_address and type:
            claim = db.session.query(UserClaim).with_for_update(of=UserClaim).filter(
                UserClaim.type == type,
                UserClaim.token == token,
                UserClaim.email_address == email_address,
                UserClaim.claimed.is_(False)
            ).first()
            if claim and age:
                now = int(datetime.utcnow().strftime('%s'))
                if int(claim.created_at.strftime('%s')) < (now - int(age)):
                    return None
            if claim:
                claim.claimed = True
                self.save(claim)
                claimed = True
        return claim if claimed else None
