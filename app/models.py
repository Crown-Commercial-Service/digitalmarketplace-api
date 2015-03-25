from . import db
from sqlalchemy.dialects.postgresql import JSON

from sqlalchemy import *


class Supplier(db.Model):
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.BigInteger,
                            index=True, unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.String,
                           index=True, unique=True, nullable=False)
    supplier_id = db.Column(db.BigInteger,
                            db.ForeignKey('suppliers.supplier_id'),
                            index=True, unique=False, nullable=False)
    created_at = db.Column(db.DateTime, index=False, unique=False,
                           nullable=False)
    updated_at = db.Column(db.DateTime, index=False, unique=False,
                           nullable=False)
    updated_by = db.Column(db.String, index=False, unique=False,
                           nullable=False)
    updated_reason = db.Column(db.String, index=False, unique=False,
                               nullable=False)
    data = db.Column(JSON)

    status = db.Column(db.String, index=False, unique=False, nullable=False)

    supplier = db.relationship(Supplier, lazy='joined', innerjoin=True)


class ArchivedService(db.Model):
    __tablename__ = 'archived_services'

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.String,
                           index=True, unique=False, nullable=False)
    supplier_id = db.Column(db.BigInteger,
                            db.ForeignKey('suppliers.supplier_id'),
                            index=True, unique=False, nullable=False)
    created_at = db.Column(db.DateTime, index=False, unique=False,
                           nullable=False)
    updated_at = db.Column(db.DateTime, index=False, unique=False,
                           nullable=False)
    updated_by = db.Column(db.String, index=False, unique=False,
                           nullable=False)
    updated_reason = db.Column(db.String, index=False, unique=False,
                               nullable=False)
    data = db.Column(JSON)

    status = db.Column(db.String, index=False, unique=False, nullable=False)

    supplier = db.relationship(Supplier, lazy='joined', innerjoin=True)

    @staticmethod
    def from_service(service):
        return ArchivedService(
            service_id=service.service_id,
            supplier_id=service.supplier_id,
            created_at=service.created_at,
            updated_at=service.updated_at,
            updated_by=service.updated_by,
            updated_reason=service.updated_reason,
            data=service.data,
            status=service.status
        )
