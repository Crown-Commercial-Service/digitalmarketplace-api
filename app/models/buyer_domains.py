from app import db


class BuyerEmailDomain(db.Model):
    __tablename__ = 'buyer_email_domains'

    id = db.Column(db.Integer, primary_key=True)
    domain_name = db.Column(db.String(), nullable=False)

    def serialize(self):
        return {
            "id": self.id,
            "domain_name": self.domain_name,
        }
