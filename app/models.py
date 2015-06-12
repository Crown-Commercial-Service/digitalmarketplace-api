from datetime import datetime

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy_utils import generic_relationship
from dmutils.audit import AuditTypes

from . import db
from .utils import link, url_for


class Framework(db.Model):
    __tablename__ = 'frameworks'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    expired = db.Column(db.Boolean, index=False, unique=False,
                        nullable=False)


class ContactInformation(db.Model):
    __tablename__ = 'contact_information'

    id = db.Column(db.Integer, primary_key=True)

    supplier_id = db.Column(db.Integer,
                            db.ForeignKey('suppliers.supplier_id'))

    contact_name = db.Column(db.String, index=False,
                             unique=False, nullable=False)

    phone_number = db.Column(db.String, index=False,
                             unique=False, nullable=True)

    email = db.Column(db.String, index=False,
                      unique=False, nullable=False)

    website = db.Column(db.String, index=False,
                        unique=False, nullable=True)

    address1 = db.Column(db.String, index=False,
                         unique=False, nullable=True)

    address2 = db.Column(db.String, index=False,
                         unique=False, nullable=True)

    city = db.Column(db.String, index=False,
                     unique=False, nullable=True)

    country = db.Column(db.String, index=False,
                        unique=False, nullable=True)

    postcode = db.Column(db.String, index=False,
                         unique=False, nullable=False)

    def update_from_json(self, data):
        self.contact_name = data.get("contactName")
        self.phone_number = data.get("phoneNumber")
        self.email = data.get("email")
        self.website = data.get("website")
        self.address1 = data.get("address1")
        self.address2 = data.get("address2")
        self.city = data.get("city")
        self.country = data.get("country")
        self.postcode = data.get("postcode")

        return self

    def serialize(self):
        links = link(
            "self", url_for(".update_contact_information",
                            supplier_id=self.supplier_id,
                            contact_id=self.id)
        )

        serialized = {
            'id': self.id,
            'contactName': self.contact_name,
            'phoneNumber': self.phone_number,
            'email': self.email,
            'website': self.website,
            'address1': self.address1,
            'address2': self.address2,
            'city': self.city,
            'country': self.country,
            'postcode': self.postcode,
            'links': links,
        }

        return filter_null_value_fields(serialized)


class Supplier(db.Model):
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)

    supplier_id = db.Column(db.BigInteger,
                            index=True, unique=True, nullable=False)

    name = db.Column(db.String(255), nullable=False)

    description = db.Column(db.String, index=False,
                            unique=False, nullable=True)

    contact_information = db.relationship(ContactInformation,
                                          backref='supplier',
                                          lazy='joined',
                                          innerjoin=False)

    duns_number = db.Column(db.String, index=False,
                            unique=False, nullable=True)

    esourcing_id = db.Column(db.String, index=False,
                             unique=False, nullable=True)

    clients = db.Column(JSON, default=list)

    def serialize(self):
        links = link(
            "self", url_for(".get_supplier", supplier_id=self.supplier_id)
        )

        contact_information_list = []
        for contact_information_instance in self.contact_information:
            contact_information_list.append(
                contact_information_instance.serialize()
            )

        serialized = {
            'id': self.supplier_id,
            'name': self.name,
            'description': self.description,
            'dunsNumber': self.duns_number,
            'eSourcingId': self.esourcing_id,
            'contactInformation': contact_information_list,
            'links': links,
            'clients': self.clients
        }

        return filter_null_value_fields(serialized)

    def update_from_json(self, data):
        self.name = data.get('name')
        self.description = data.get('description')
        self.duns_number = data.get('dunsNumber')
        self.esourcing_id = data.get('eSourcingId')
        self.clients = data.get('clients')

        return self


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=False, unique=False,
                     nullable=False)
    email_address = db.Column(db.String, index=True, unique=True,
                              nullable=False)
    password = db.Column(db.String, index=False, unique=False,
                         nullable=False)
    active = db.Column(db.Boolean, index=False, unique=False,
                       nullable=False)
    locked = db.Column(db.Boolean, index=False, unique=False,
                       nullable=False)
    created_at = db.Column(db.DateTime, index=False, unique=False,
                           nullable=False)
    updated_at = db.Column(db.DateTime, index=False, unique=False,
                           nullable=False)
    password_changed_at = db.Column(db.DateTime, index=False, unique=False,
                                    nullable=False)
    role = db.Column(db.String, index=False, unique=False, nullable=False)

    supplier_id = db.Column(db.BigInteger,
                            db.ForeignKey('suppliers.supplier_id'),
                            index=True, unique=False, nullable=True)

    supplier = db.relationship(Supplier, lazy='joined', innerjoin=False)

    def serialize(self):
        user = {
            'id': self.id,
            'emailAddress': self.email_address,
            'name': self.name,
            'role': self.role,
            'active': self.active,
            'locked': self.locked,
            'createdAt': self.created_at,
            'updatedAt': self.updated_at,
            'passwordChangedAt': self.password_changed_at
        }

        if self.role == 'supplier':
            supplier = {
                "supplierId": self.supplier.supplier_id,
                "name": self.supplier.name
            }
            user['supplier'] = supplier

        return user


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
    data = db.Column(JSON)

    framework_id = db.Column(db.BigInteger,
                             db.ForeignKey('frameworks.id'),
                             index=True, unique=False, nullable=False)

    status = db.Column(db.String, index=False, unique=False, nullable=False)

    supplier = db.relationship(Supplier, lazy='joined', innerjoin=True)

    framework = db.relationship(Framework, lazy='joined', innerjoin=True)

    def serialize(self):
        """
        :return: dictionary representation of a service
        """

        data = dict(self.data.items())

        data.update({
            'id': self.service_id,
            'supplierId': self.supplier.supplier_id,
            'supplierName': self.supplier.name,
            'frameworkName': self.framework.name,
            'status': self.status
        })

        data['links'] = link(
            "self", url_for(".get_service", service_id=data['id'])
        )

        return data

    def update_from_json(self, data):
        self.service_id = str(data.pop('id', self.service_id))

        data.pop('supplierId', None)
        data.pop('supplierName', None)
        data.pop('frameworkName', None)
        data.pop('status', None)
        data.pop('links', None)

        current_data = dict(self.data.items())
        current_data.update(data)
        self.data = current_data

        now = datetime.utcnow()
        self.updated_at = now


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
            data=service.data,
            status=service.status
        )

    def serialize(self):
        """
        :return: dictionary representation of a service
        """

        data = dict(self.data.items())

        data.update({
            'id': self.service_id,
            'supplierId': self.supplier.supplier_id,
            'supplierName': self.supplier.name,
        })

        data['links'] = link(
            "self", url_for(".get_service", service_id=data['id'])
        )

        return data


class DraftService(db.Model):
    __tablename__ = 'draft_services'

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
    data = db.Column(JSON)

    framework_id = db.Column(db.BigInteger,
                             db.ForeignKey('frameworks.id'),
                             index=True, unique=False, nullable=False)

    status = db.Column(db.String, index=False, unique=False, nullable=False)

    supplier = db.relationship(Supplier, lazy='joined', innerjoin=True)

    framework = db.relationship(Framework, lazy='joined', innerjoin=True)

    @staticmethod
    def from_service(service):
        now = datetime.now(),
        return DraftService(
            framework_id=service.framework_id,
            service_id=service.service_id,
            supplier_id=service.supplier_id,
            created_at=now,
            updated_at=now,
            data=service.data,
            status=service.status
        )

    def serialize(self):
        """
        :return: dictionary representation of a draft service
        """

        data = dict(self.data.items())

        data.update({
            'id': self.id,
            'service_id': self.service_id,
            'supplierId': self.supplier.supplier_id,
            'status': self.status
        })

        data['links'] = link(
            "self", url_for(".fetch_draft_service", service_id=self.service_id)
        )

        return data

    def update_from_json(self, data):
        self.service_id = str(data.pop('id', self.service_id))

        data.pop('supplierId', None)
        data.pop('supplierName', None)
        data.pop('frameworkName', None)
        data.pop('status', None)
        data.pop('links', None)

        current_data = dict(self.data.items())
        current_data.update(data)
        self.data = current_data

        now = datetime.now()
        self.updated_at = now


class AuditEvent(db.Model):
    __tablename__ = 'audit_events'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.utcnow)
    user = db.Column(db.String)
    data = db.Column(JSON)

    object_type = db.Column(db.String)
    object_id = db.Column(db.BigInteger)

    object = generic_relationship(
        object_type, object_id
    )

    def __init__(self, audit_type, user, data, db_object):
        self.type = audit_type.value
        self.data = data
        self.object = db_object
        self.user = user

    def serialize(self):
        """
        :return: dictionary representation of an audit event
        """

        data = {
            'id': self.id,
            'type': self.type,
            'user': self.user,
            'data': self.data,
            'createdAt': self.created_at.strftime("%Y-%m-%dT%H:%M:%S%Z"),
            'links': link(
                "self", url_for(".list_audits"))
        }

        return data


def filter_null_value_fields(obj):
    return dict(
        filter(lambda x: x[1] is not None, obj.items())
    )
