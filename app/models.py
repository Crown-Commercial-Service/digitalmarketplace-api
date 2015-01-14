from . import db
from sqlalchemy.dialects.postgresql import JSON


class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(JSON)
