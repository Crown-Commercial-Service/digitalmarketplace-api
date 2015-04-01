from . import db
from flask import url_for as base_url_for
from sqlalchemy.dialects.postgresql import JSON


class DbModelExtended(db.Model):
    """
    Wrapper for db.Model that can be extended with other methods
    """
    __abstract__ = True

    @staticmethod
    def link(rel, href):
        if href is not None:
            return {
                "rel": rel,
                "href": href,
            }

    @staticmethod
    def url_for(*args, **kwargs):
        kwargs.setdefault('_external', True)
        return base_url_for(*args, **kwargs)

    @classmethod
    def pagination_links(cls, pagination, endpoint, args):
        return [
            cls.link(rel, cls.url_for(endpoint,
                                      **dict(list(args.items()) +
                                             list({'page': page}.items()))))
            for rel, page in [('next', pagination.next_num),
                              ('prev', pagination.prev_num)]
            if 0 < page <= pagination.pages
        ]


class Framework(db.Model):
    __tablename__ = 'frameworks'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False)

    expired = db.Column(db.Boolean, index=False, unique=False,
                        nullable=False)


class Supplier(DbModelExtended):

    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.BigInteger,
                            index=True, unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)

    def serialize(self):
        links = [
            self.link(
                "self",
                self.url_for(".get_supplier", supplier_id=self.supplier_id)
            ),
            self.link(
                "suppliers.list",
                self.url_for(".get_suppliers_by_prefix")
            )
        ]

        return {
            'id': self.supplier_id,
            'name': self.name,
            'links': links
        }


class Service(DbModelExtended):
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

    framework_id = db.Column(db.BigInteger,
                             db.ForeignKey('frameworks.id'),
                             index=True, unique=False, nullable=False)

    status = db.Column(db.String, index=False, unique=False, nullable=False)

    supplier = db.relationship(Supplier, lazy='joined', innerjoin=True)

    framework = db.relationship(Framework, lazy='joined', innerjoin=True)

    def serialize(self):
        links = [
            self.link(
                "self",
                self.url_for(".get_service", service_id=self.data['id'])
            ),
        ]

        return {
            'id': self.service_id,
            'supplierId': self.supplier.supplier_id,
            'supplierName': self.supplier.name,
            'createdAt': self.created_at,
            'updatedAt': self.updated_at,
            'updatedBy': self.updated_by,
            'updatedReason': self.updated_reason,
            'data': self.data,
            'links': links
        }
    

class ArchivedService(DbModelExtended):
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

    framework_id = db.Column(db.BigInteger,
                             db.ForeignKey('frameworks.id'),
                             index=True, unique=False, nullable=False)

    status = db.Column(db.String, index=False, unique=False, nullable=False)

    supplier = db.relationship(Supplier, lazy='joined', innerjoin=True)

    framework = db.relationship(Framework, lazy='joined', innerjoin=True)

    @staticmethod
    def from_service(service):
        return ArchivedService(
            framework_id=service.framework_id,
            service_id=service.service_id,
            supplier_id=service.supplier_id,
            created_at=service.created_at,
            updated_at=service.updated_at,
            updated_by=service.updated_by,
            updated_reason=service.updated_reason,
            data=service.data,
            status=service.status
        )
