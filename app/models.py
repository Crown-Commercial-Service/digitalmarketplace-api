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

    address1 = db.Column(db.String(255))
    address2 = db.Column(db.String(255))
    city = db.Column(db.String(255))
    country = db.Column(db.String(255))
    postcode = db.Column(db.String(255))

    contact_email = db.Column(db.String(255))
    contact_name = db.Column(db.String(255))
    contact_phone = db.Column(db.String(255))

    company_number = db.Column(db.String(255))
    duns_number = db.Column(db.String(255))
    vat_number = db.Column(db.String(255))
    vendor_id = db.Column(db.String(255))
    esourcing_id = db.Column(db.String(255))

    url_key = db.Column(db.String(255))
    website = db.Column(db.String(255))

    description = db.Column(db.String(5000))
    clients_string = db.Column(db.String(1000))
