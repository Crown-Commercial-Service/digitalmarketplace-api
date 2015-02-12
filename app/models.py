from . import db
from sqlalchemy.dialects.postgresql import JSON


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.BigInteger,
                           index=True, unique=True, nullable=False)
    supplier_id = db.Column(db.BigInteger, index=True, unique=False,
                            nullable=False)
    created_at = db.Column(db.DateTime, index=False, unique=False,
                           nullable=False)
    updated_at = db.Column(db.DateTime, index=False, unique=False,
                           nullable=False)
    data = db.Column(JSON)


class Supplier(db.Model):
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
