import random
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import pytz
import re

from flask import current_app
from flask_sqlalchemy import BaseQuery
from six import string_types

from sqlalchemy import asc, desc
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSON, INTERVAL
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import case as sql_case
from sqlalchemy.sql.expression import cast as sql_cast
from sqlalchemy.types import String
from sqlalchemy import Sequence
from sqlalchemy_utils import generic_relationship
from dmutils.data_tools import ValidationError, normalise_abn, normalise_acn, parse_money
from dmutils.formats import DATETIME_FORMAT
from dmutils.dates import get_publishing_dates

from . import db
from .utils import link, url_for, strip_whitespace_from_data, drop_foreign_fields, purge_nulls_from_data
from .validation import is_valid_service_id, is_valid_buyer_email, get_validation_errors


def getUtcTimestamp():
    return datetime.now(pytz.utc)


class FrameworkLot(db.Model):
    __tablename__ = 'framework_lot'

    framework_id = db.Column(db.Integer, db.ForeignKey('framework.id'), primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('lot.id'), primary_key=True)


class Lot(db.Model):
    __tablename__ = 'lot'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, nullable=False, index=True)
    name = db.Column(db.String, nullable=False)
    one_service_limit = db.Column(db.Boolean, nullable=False, default=False)
    data = db.Column(JSON)

    @property
    def allows_brief(self):
        return self.one_service_limit

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.name)

    def serialize(self):
        data = dict(self.data.items())
        data.update({
            'id': self.id,
            'slug': self.slug,
            'name': self.name,
            'oneServiceLimit': self.one_service_limit,
            'allowsBrief': self.allows_brief,
        })
        return data


class Framework(db.Model):
    __tablename__ = 'framework'

    STATUSES = (
        'coming', 'open', 'pending', 'standstill', 'live', 'expired'
    )
    FRAMEWORKS = (
        'g-cloud',
        'dos',
    )

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, nullable=False, unique=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    framework = db.Column(db.String(), index=True, nullable=False)
    framework_agreement_details = db.Column(JSON, nullable=True)
    status = db.Column(db.String(),
                       index=True, nullable=False,
                       default='pending')
    clarification_questions_open = db.Column(db.Boolean, nullable=False, default=False)
    lots = db.relationship(
        'Lot', secondary="framework_lot",
        lazy='joined', innerjoin=False,
        order_by=Lot.id,
        backref='frameworks'
    )

    def get_lot(self, lot_slug):
        return next(
            (lot for lot in self.lots if lot.slug == lot_slug),
            None
        )

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'framework': self.framework,
            'frameworkAgreementVersion': (self.framework_agreement_details or {}).get("frameworkAgreementVersion"),
            'status': self.status,
            'clarificationQuestionsOpen': self.clarification_questions_open,
            'lots': [lot.serialize() for lot in self.lots],
        }

    @validates('status')
    def validates_status(self, key, value):
        if value not in self.STATUSES:
            raise ValidationError("Invalid status value '{}'".format(value))

        return value

    @validates('framework')
    def validates_framework(self, key, framework):
        if framework not in self.FRAMEWORKS:
            raise ValidationError("Invalid framework value '{}'".format(framework))
        return framework

    slug_pattern = re.compile("^[\w-]+$")

    @validates("slug")
    def validates_slug(self, key, slug):
        if not self.slug_pattern.match(slug):
            raise ValidationError("Invalid slug value '{}'".format(slug))
        return slug

    def __repr__(self):
        return '<{}: {} slug={}>'.format(self.__class__.__name__, self.name, self.slug)


class WebsiteLink(db.Model):
    __tablename__ = 'website_link'

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String, index=False, nullable=False)
    label = db.Column(db.String, index=False, nullable=False)

    @staticmethod
    def from_json(as_dict):
        try:
            return WebsiteLink(url=as_dict.get('url'),
                               label=as_dict.get('label'))
        except KeyError, e:
            raise ValidationError('Website link missing required field: {}'.format(e))

    def serialize(self):
        serialized = {
            'url': self.url,
            'label': self.label,
        }
        return serialized


class Address(db.Model):
    __tablename__ = 'address'

    id = db.Column(db.Integer, primary_key=True)
    address_line = db.Column(db.String, index=False, nullable=True)
    suburb = db.Column(db.String, index=False, nullable=True)
    state = db.Column(db.String, index=False, nullable=False)
    postal_code = db.Column(db.String(8), index=False, nullable=False)
    country = db.Column(db.String, index=False, nullable=False, default='Australia')

    @staticmethod
    def from_json(as_dict):
        try:
            return Address(address_line=as_dict.get('addressLine'),
                           suburb=as_dict.get('suburb'),
                           state=as_dict.get('state'),
                           postal_code=as_dict.get('postalCode'),
                           country=as_dict.get('country', 'Australia'))
        except KeyError, e:
            raise ValidationError('Contact missing required field: {}'.format(e))

    def serialize(self):
        serialized = {
            'addressLine': self.address_line,
            'suburb': self.suburb,
            'state': self.state,
            'postalCode': self.postal_code,
            'country': self.country,
        }
        return filter_null_value_fields(serialized)

    @validates('postal_code')
    def validate_postal_code(self, key, code):
        code = str(code)
        if re.match('[0-9]{4}', code) is None:
            raise ValidationError('Invalid postal code: {}'.format(code))
        return code


class Contact(db.Model):
    __tablename__ = 'contact'

    id = db.Column(db.Integer, primary_key=True)
    contact_for = db.Column(db.String, index=False, nullable=True)
    name = db.Column(db.String, index=False, nullable=False)
    role = db.Column(db.String, index=False, nullable=True)
    email = db.Column(db.String, index=False, nullable=True)
    phone = db.Column(db.String, index=False, nullable=True)
    fax = db.Column(db.String, index=False, nullable=True)

    @staticmethod
    def from_json(as_dict):
        try:
            return Contact(contact_for=as_dict.get('contactFor', None),
                           name=as_dict.get('name'),
                           role=as_dict.get('role', None),
                           email=as_dict.get('email', None),
                           phone=as_dict.get('phone', None),
                           fax=as_dict.get('fax', None))
        except KeyError, e:
            raise ValidationError('Contact missing required field: {}'.format(e))

    def serialize(self):
        serialized = {
            'contactFor': self.contact_for,
            'name': self.name,
            'role': self.role,
            'email': self.email,
            'phone': self.phone,
            'fax': self.fax,
        }
        return filter_null_value_fields(serialized)


class SupplierReference(db.Model):
    __tablename__ = 'supplier_reference'

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id', ondelete='cascade'))
    name = db.Column(db.String, index=False, nullable=False)
    organisation = db.Column(db.String, index=False, nullable=False)
    role = db.Column(db.String, index=False, nullable=True)
    email = db.Column(db.String, index=False, nullable=False)

    @staticmethod
    def from_json(as_dict):
        try:
            return SupplierReference(name=as_dict.get('name'),
                                     organisation=as_dict.get('organisation'),
                                     role=as_dict.get('role', None),
                                     email=as_dict.get('email'))
        except KeyError, e:
            raise ValidationError('Supplier reference missing required field: {}'.format(e))

    def serialize(self):
        serialized = {
            'name': self.name,
            'organisation': self.organisation,
            'role': self.role,
            'email': self.email,
        }
        return filter_null_value_fields(serialized)


class ServiceCategory(db.Model):
    __tablename__ = 'service_category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    abbreviation = db.Column(db.String(15), nullable=False)

    @staticmethod
    def lookup(as_dict):
        name = as_dict.get('name', 'no category specified')
        result = ServiceCategory.query.filter_by(name=name).first()
        if result is None:
            raise ValidationError('Unknown category: {}'.format(name))
        return result

    def serialize(self):
        serialized = {
            'name': self.name,
        }
        return serialized


class ServiceRole(db.Model):
    __tablename__ = 'service_role'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('service_category.id'), nullable=False)
    category = db.relationship('ServiceCategory')
    name = db.Column(db.String, nullable=False)
    abbreviation = db.Column(db.String(15), nullable=False)

    @staticmethod
    def lookup(as_dict):
        category_name = as_dict.get('category', 'no category specified')
        category = ServiceCategory.lookup({'name': category_name})
        role_name = as_dict.get('role', 'no role specified')
        result = ServiceRole.query.filter_by(name=role_name).first()
        if result is None:
            raise ValidationError('Unknown role: {}'.format(role_name))
        return result

    def serialize(self):
        serialized = {
            'category': self.category.name,
            'role': self.name,
        }
        return serialized


class PriceSchedule(db.Model):
    __tablename__ = 'price_schedule'

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id', ondelete='cascade'), nullable=False)
    service_role_id = db.Column(db.Integer, db.ForeignKey('service_role.id'), nullable=False)
    service_role = db.relationship('ServiceRole')
    hourly_rate = db.Column(db.Numeric)
    daily_rate = db.Column(db.Numeric)
    gst_included = db.Column(db.Boolean, index=False, nullable=False, default=True)

    __table_args__ = (db.UniqueConstraint('supplier_id', 'service_role_id'),)

    @staticmethod
    def from_json(as_dict):
        try:
            return PriceSchedule(service_role=ServiceRole.lookup(as_dict.get('serviceRole')),
                                 hourly_rate=as_dict.get('hourlyRate'),
                                 daily_rate=as_dict.get('dailyRate'),
                                 gst_included=as_dict.get('gstIncluded'))
        except KeyError, e:
            raise ValidationError('Price schedule missing required field: {}'.format(e))
        except InvalidOperation, e:
            raise ValidationError('Invalid rate value: {}'.format(e))

    def serialize(self):
        serialized = {
            'serviceRole': self.service_role.serialize(),
            'hourlyRate': str(self.hourly_rate),
            'dailyRate': str(self.daily_rate),
            'gstIncluded': self.gst_included,
        }
        return serialized

    @validates('hourly_rate', 'daily_rate')
    def validate_rate(self, key, rate):
        if rate is None:
            return None
        if type(rate) is str or type(rate) is unicode:
            return parse_money(rate)
        return rate


supplier__extra_links = db.Table('supplier__extra_links',
                                 db.Column('supplier_id',
                                           db.Integer,
                                           db.ForeignKey('supplier.id', ondelete='cascade'),
                                           nullable=False),
                                 db.Column('website_link_id',
                                           db.Integer,
                                           db.ForeignKey('website_link.id'),
                                           nullable=False),
                                 db.PrimaryKeyConstraint('supplier_id', 'website_link_id'))


supplier__contact = db.Table('supplier__contact',
                             db.Column('supplier_id',
                                       db.Integer,
                                       db.ForeignKey('supplier.id', ondelete='cascade'),
                                       nullable=False),
                             db.Column('contact_id',
                                       db.Integer,
                                       db.ForeignKey('contact.id'),
                                       nullable=False),
                             db.PrimaryKeyConstraint('supplier_id', 'contact_id'))


class Supplier(db.Model):
    __tablename__ = 'supplier'

    id = db.Column(db.Integer, primary_key=True)
    data_version = db.Column(db.Integer, index=False)
    code = db.Column(db.BigInteger, index=True, unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    long_name = db.Column(db.String(255), nullable=True)
    summary = db.Column(db.String(511), index=False, nullable=True)
    description = db.Column(db.String, index=False, nullable=True)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'), index=False, nullable=False)
    address = db.relationship('Address', single_parent=True, cascade='all, delete-orphan')
    website = db.Column(db.String(255), index=False, nullable=True)
    extra_links = db.relationship('WebsiteLink',
                                  secondary=supplier__extra_links,
                                  single_parent=True,
                                  cascade='all, delete-orphan')
    abn = db.Column(db.String(15), nullable=True)
    acn = db.Column(db.String(15), nullable=True)
    contacts = db.relationship('Contact', secondary=supplier__contact, single_parent=True, cascade='all, delete-orphan')
    references = db.relationship('SupplierReference', single_parent=True, cascade='all, delete-orphan')
    prices = db.relationship('PriceSchedule', single_parent=True, cascade='all, delete-orphan')
    creation_time = db.Column(db.DateTime(timezone=True),
                              index=False,
                              nullable=False,
                              default=getUtcTimestamp)
    # FIXME: remove meaningless default value after schema migration
    last_update_time = db.Column(db.DateTime(timezone=True),
                                 index=False,
                                 nullable=False,
                                 default=getUtcTimestamp)

    def get_service_counts(self):
        # FIXME: To be removed from Australian version
        return {}

    def get_link(self):
        return url_for(".get_supplier", code=self.code)

    def serialize(self, data=None):
        serialized = {
            'code': self.code,
            'dataVersion': self.data_version,
            'name': self.name,
            'longName': self.long_name,
            'address': self.address.serialize(),
            'summary': self.summary,
            'description': self.description,
            'website': self.website,
            'extraLinks': [l.serialize() for l in self.extra_links],
            'abn': self.abn,
            'acn': self.acn,
            'contacts': [c.serialize() for c in self.contacts],
            'references': [r.serialize() for r in self.references],
            'prices': [p.serialize() for p in self.prices],
            'creationTime': self.creation_time.strftime(DATETIME_FORMAT),
            'lastUpdateTime': self.last_update_time.strftime(DATETIME_FORMAT),
        }
        serialized.update(data or {})
        return serialized

    def update_from_json(self, data):
        keys = ('code', 'dataVersion', 'name', 'longName', 'summary', 'description', 'address', 'website', 'extraLinks',
                'abn', 'acn', 'contacts', 'references', 'prices')
        extra_keys = set(data.keys()) - set(keys)
        if extra_keys:
            raise ValidationError('Additional properties are not allowed: {}'.format(str(extra_keys)))
        self.code = data.get('code', self.code)
        self.data_version = data.get('dataVersion', self.data_version)
        self.name = data.get('name', self.name)
        self.long_name = data.get('longName', self.long_name)
        self.summary = data.get('summary', self.summary)
        self.description = data.get('description', self.description)
        self.website = data.get('website', self.website)
        self.abn = data.get('abn', self.abn)
        self.acn = data.get('acn', self.acn)
        if 'address' in data:
            self.address = Address.from_json(data['address'])
        if 'extraLinks' in data:
            self.extra_links = [WebsiteLink.from_json(l) for l in data['extraLinks']]
        if 'contacts' in data:
            self.contacts = [Contact.from_json(c) for c in data['contacts']]
        if 'references' in data:
            self.references = [SupplierReference.from_json(r) for r in data['references']]
        if 'prices' in data:
            self.prices = [PriceSchedule.from_json(p) for p in data['prices']]
        self.last_update_time = getUtcTimestamp()
        return self

    @validates('name')
    def validate_name(self, key, name):
        if not name:
            raise ValidationError('Supplier name required')
        return name.strip()

    @validates('long_name')
    def validate_long_name(self, key, long_name):
        if not long_name:
            return None
        return long_name.strip()

    @validates('acn')
    def validate_acn(self, key, acn):
        if acn is not None:
            acn = normalise_acn(acn)
        return acn

    @validates('abn')
    def validate_abn(self, key, abn):
        if abn is not None:
            abn = normalise_abn(abn)
        return abn


class SupplierFramework(db.Model):
    __tablename__ = 'supplier_framework'

    supplier_code = db.Column(db.BigInteger,
                              db.ForeignKey('supplier.code'),
                              primary_key=True)
    framework_id = db.Column(db.Integer,
                             db.ForeignKey('framework.id'),
                             primary_key=True)
    declaration = db.Column(JSON)
    on_framework = db.Column(db.Boolean, nullable=True)
    agreement_returned_at = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    countersigned_at = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    agreement_details = db.Column(JSON)

    supplier = db.relationship(Supplier, lazy='joined', innerjoin=True)
    framework = db.relationship(Framework, lazy='joined', innerjoin=True)

    @validates('declaration')
    def validates_declaration(self, key, value):
        value = strip_whitespace_from_data(value)
        value = purge_nulls_from_data(value)

        return value

    @validates('agreement_details')
    def validates_agreement_details(self, key, value):
        if value is None:
            return value

        value = strip_whitespace_from_data(value)
        value = purge_nulls_from_data(value)

        return value

    @staticmethod
    def find_by_framework(framework_slug):
        return SupplierFramework.query.filter(
            SupplierFramework.framework.has(
                Framework.slug == framework_slug)
        )

    @staticmethod
    def find_by_supplier_and_framework(supplier_code, framework_slug):
        return SupplierFramework.find_by_framework(framework_slug).filter(
            SupplierFramework.supplier_code == supplier_code
        ).first()

    @staticmethod
    def get_service_counts(supplier_code):

        count_services_query = db.session.query(
            Service.framework_id, Service.status, func.count()
        ).filter(
            Service.supplier_code == supplier_code
        ).group_by(
            Service.framework_id,
            Service.status
        ).all()

        count_drafts_query = db.session.query(
            DraftService.framework_id, DraftService.status, func.count()
        ).filter(
            DraftService.supplier_code == supplier_code
        ).group_by(
            DraftService.framework_id,
            DraftService.status
        ).all()

        return {
            (row[0], row[1]): row[2]
            for row in count_services_query + count_drafts_query
        }

    def serialize(self, data=None):
        agreement_returned_at = self.agreement_returned_at
        if agreement_returned_at:
            agreement_returned_at = agreement_returned_at.strftime(DATETIME_FORMAT)

        countersigned_at = self.countersigned_at
        if countersigned_at:
            countersigned_at = countersigned_at.strftime(DATETIME_FORMAT)

        supplier_framework = dict({
            "supplierCode": self.supplier_code,
            "supplierName": self.supplier.name,
            "frameworkSlug": self.framework.slug,
            "declaration": self.declaration,
            "onFramework": self.on_framework,
            "agreementReturned": bool(agreement_returned_at),
            "agreementReturnedAt": agreement_returned_at,
            "agreementDetails": self.agreement_details,
            "countersigned": bool(countersigned_at),
            "countersignedAt": countersigned_at,
        }, **(data or {}))

        if self.agreement_details and self.agreement_details.get('uploaderUserId'):
            user = User.query.filter(
                User.id == self.agreement_details.get('uploaderUserId')
            ).first()

            if user:
                supplier_framework['agreementDetails']['uploaderUserName'] = user.name
                supplier_framework['agreementDetails']['uploaderUserEmail'] = user.email_address

        return supplier_framework


class User(db.Model):
    __tablename__ = 'user'

    ROLES = [
        'buyer',
        'supplier',
        'admin',               # a general admin user, with permission to do most (but not all)
                               # admin actions.
        'admin-ccs-category',  # generally restricted to read-only access to admin views.
        'admin-ccs-sourcing',  # can perform admin actions involving supplier acceptance.
    ]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=False, unique=False,
                     nullable=False)
    email_address = db.Column(db.String, index=True, unique=True,
                              nullable=False)
    phone_number = db.Column(db.String, index=False, unique=False,
                             nullable=True)
    password = db.Column(db.String, index=False, unique=False,
                         nullable=False)

    # used to disable accounts
    active = db.Column(db.Boolean, index=False, unique=False,
                       nullable=False)

    created_at = db.Column(db.DateTime, index=False, unique=False,
                           nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, index=False, unique=False,
                           nullable=False, default=datetime.utcnow,
                           onupdate=datetime.utcnow)
    password_changed_at = db.Column(db.DateTime, index=False, unique=False,
                                    nullable=False)
    logged_in_at = db.Column(db.DateTime, nullable=True)

    # used to determine whether account is `locked`. field is reset upon successful login or can
    # be reset manually to "unlock" an account.
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)

    # used by frontends to determine whether view access should be allowed
    role = db.Column(db.Enum(*ROLES, name='user_roles_enum'), index=False, unique=False, nullable=False)

    # FIXME: should be a many-to-many
    supplier_code = db.Column(db.BigInteger,
                              db.ForeignKey('supplier.code'),
                              index=True, unique=False, nullable=True)

    supplier = db.relationship(Supplier, lazy='joined', innerjoin=False)

    @validates('email_address')
    def validate_email_address(self, key, value):
        if value and self.role == 'buyer' and not is_valid_buyer_email(value):
            raise ValidationError("invalid_buyer_domain")
        return value

    @validates('role')
    def validate_role(self, key, value):
        if self.email_address and value == 'buyer' and not is_valid_buyer_email(self.email_address):
            raise ValidationError("invalid_buyer_domain")
        return value

    @property
    def locked(self):
        """
            Whether account has had too many failed login attempts (since counter last reset)
        """
        login_attempt_limit = current_app.config['DM_FAILED_LOGIN_LIMIT']
        return self.failed_login_count >= login_attempt_limit

    @staticmethod
    def get_by_email_address(email_address):
        return User.query.filter(
            User.email_address == email_address
        ).first()

    def get_link(self):
        return url_for('.get_user_by_id', user_id=self.id)

    def serialize(self):
        user = {
            'id': self.id,
            'emailAddress': self.email_address,
            'phoneNumber': self.phone_number,
            'name': self.name,
            'role': self.role,
            'active': self.active,
            'locked': self.locked,
            'createdAt': self.created_at.strftime(DATETIME_FORMAT),
            'updatedAt': self.updated_at.strftime(DATETIME_FORMAT),
            'passwordChangedAt':
                self.password_changed_at.strftime(DATETIME_FORMAT),
            'loggedInAt': self.logged_in_at.strftime(DATETIME_FORMAT)
                if self.logged_in_at else None,
            'failedLoginCount': self.failed_login_count,
        }

        if self.role == 'supplier':
            supplier = {
                "supplierCode": self.supplier.code,
                "name": self.supplier.name
            }
            user['supplier'] = supplier

        return user


class ServiceTableMixin(object):

    STATUSES = ('disabled', 'enabled', 'published')

    # not used as the externally-visible "pk" by actual Services in favour of service_id
    id = db.Column(db.Integer, primary_key=True)

    # used as externally-visible "pk" for Services and allows services identity to be tracked
    # across a service's lifetime. assigned randomly (see generate_new_service_id) at DraftService ->
    # Service publishing time.
    service_id = db.Column(db.String, index=True, unique=True, nullable=False)

    data = db.Column(JSON)
    status = db.Column(db.String, index=False, unique=False, nullable=False)

    created_at = db.Column(db.DateTime, index=False, nullable=False,
                           default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, index=False, nullable=False,
                           default=datetime.utcnow, onupdate=datetime.utcnow)

    @declared_attr
    def supplier_code(cls):
        return db.Column(db.BigInteger, db.ForeignKey('supplier.code'),
                         index=True, unique=False, nullable=False)

    @declared_attr
    def framework_id(cls):
        return db.Column(db.BigInteger, db.ForeignKey('framework.id'),
                         index=True, unique=False, nullable=False)

    @declared_attr
    def __table_args__(cls):
        return (db.ForeignKeyConstraint([cls.framework_id, cls.lot_id],
                                        ['framework_lot.framework_id', 'framework_lot.lot_id']),
                {})

    @declared_attr
    def lot_id(cls):
        return db.Column(db.BigInteger, db.ForeignKey('lot.id'),
                         index=True, unique=False, nullable=False)

    @declared_attr
    def supplier(cls):
        return db.relationship(Supplier, lazy='joined', innerjoin=True)

    @declared_attr
    def framework(cls):
        return db.relationship(Framework, lazy='joined', innerjoin=True)

    @declared_attr
    def lot(cls):
        return db.relationship(Lot, lazy='joined', innerjoin=True)

    @validates('service_id')
    def validate_service_id(self, key, value):
        if not is_valid_service_id(value):
            raise ValidationError("Invalid service ID value '{}'".format(value))

        return value

    @validates('status')
    def validates_status(self, key, value):
        if value not in self.STATUSES:
            raise ValidationError("Invalid status value '{}'".format(value))

        return value

    @validates('data')
    def validates_data(self, key, value):
        data = drop_foreign_fields(value, [
            'id', 'status',
            'supplierCode', 'supplierName',
            'frameworkSlug', 'frameworkFramework', 'frameworkName', 'frameworkStatus',
            'lot', 'lotSlug', 'lotName',
            'updatedAt', 'createdAt', 'links'
        ])

        data = strip_whitespace_from_data(data)
        data = purge_nulls_from_data(data)

        return data

    def serialize(self):
        """
        :return: dictionary representation of a service
        """

        data = dict(self.data.items())

        data.update({
            'id': self.service_id,
            'supplierCode': self.supplier.code,
            'supplierName': self.supplier.name,
            'frameworkSlug': self.framework.slug,
            'frameworkFramework': self.framework.framework,
            'frameworkName': self.framework.name,
            'frameworkStatus': self.framework.status,
            'lot': self.lot.slug,
            'lotSlug': self.lot.slug,
            'lotName': self.lot.name,
            'updatedAt': self.updated_at.strftime(DATETIME_FORMAT),
            'createdAt': self.created_at.strftime(DATETIME_FORMAT),
            'status': self.status
        })

        data['links'] = link(
            "self", self.get_link()
        )

        return data

    def update_from_json(self, data):
        current_data = dict(self.data.items())
        current_data.update(data)

        self.data = current_data

    def __repr__(self):
        return '<{}: service_id={}, supplier_code={}, lot={}>'.format(
            self.__class__.__name__,
            self.service_id, self.supplier_code, self.lot
        )


class Service(db.Model, ServiceTableMixin):
    __tablename__ = 'service'

    @staticmethod
    def create_from_draft(draft, status):
        return Service(
            framework=draft.framework,
            lot=draft.lot,
            service_id=generate_new_service_id(draft.framework.slug),
            supplier=draft.supplier,
            data=draft.data,
            status=status
        )

    class query_class(BaseQuery):
        def framework_is_live(self):
            return self.filter(
                Service.framework.has(Framework.status == 'live'))

        def default_order(self):
            service_name = Service.data['serviceName'] \
                                  .cast(String) \
                                  .label('data_servicename')
            return self.order_by(
                asc(Service.framework_id),
                asc(Service.lot_id),
                asc(service_name))

        def has_statuses(self, *statuses):
            return self.filter(Service.status.in_(statuses))

        def has_frameworks(self, *frameworks):
            return self.filter(
                Service.framework.has(Framework.slug.in_(frameworks))
            )

        def in_lot(self, lot_slug):
            return self.filter(Service.lot.has(Lot.slug == lot_slug))

        def data_has_key(self, key_to_find):
            return self.filter(Service.data[key_to_find].astext != '')  # SQLAlchemy weirdness

        def data_key_contains_value(self, k, v):
            return self.filter(Service.data[k].astext.contains(u'"{}"'.format(v)))  # Postgres 9.3: use string matching

    def get_link(self):
        return url_for(".get_service", service_id=self.service_id)


class ArchivedService(db.Model, ServiceTableMixin):
    """
        A record of a Service's past state
    """
    __tablename__ = 'archived_service'

    # Overwrites service_id column to remove uniqueness constraint
    service_id = db.Column(db.String, index=True, unique=False, nullable=False)

    @staticmethod
    def from_service(service):
        return ArchivedService(
            framework=service.framework,
            lot=service.lot,
            service_id=service.service_id,
            supplier=service.supplier,
            created_at=service.created_at,
            updated_at=service.updated_at,
            data=service.data,
            status=service.status
        )

    @staticmethod
    def link_object(service_id):
        if service_id is None:
            return None
        return url_for(".get_archived_service",
                       archived_service_id=service_id)

    def get_link(self):
        return self.link_object(self.id)

    def update_from_json(self, data):
        raise NotImplementedError('Archived services should not be changed')


class DraftService(db.Model, ServiceTableMixin):
    __tablename__ = 'draft_service'

    STATUSES = ('not-submitted', 'submitted', 'enabled', 'disabled', 'published', 'failed')

    # Overwrites service_id column to remove uniqueness and nullable constraint
    service_id = db.Column(db.String, index=True, unique=False, nullable=True,
                           default=None)

    @staticmethod
    def from_service(service):
        return DraftService(
            framework_id=service.framework_id,
            lot=service.lot,
            service_id=service.service_id,
            supplier=service.supplier,
            data=service.data,
            status=service.status
        )

    def copy(self):
        if self.lot.one_service_limit:
            raise ValidationError("Cannot copy a '{}' draft".format(self.lot.slug))

        data = self.data.copy()
        name = data.get('serviceName', '')
        if len(name) <= 95:
            data['serviceName'] = u"{} copy".format(name)

        do_not_copy = [
            "serviceSummary",
            "termsAndConditionsDocumentURL", "pricingDocumentURL",
            "serviceDefinitionDocumentURL", "sfiaRateDocumentURL"
        ]
        data = {key: value for key, value in data.items() if key not in do_not_copy}

        return DraftService(
            framework=self.framework,
            lot=self.lot,
            supplier=self.supplier,
            data=data,
            status='not-submitted',
        )

    def serialize(self):
        data = super(DraftService, self).serialize()
        data['id'] = self.id
        if self.service_id:
            data['serviceId'] = self.service_id

        data['links']['publish'] = url_for('.publish_draft_service', draft_id=self.id)
        data['links']['complete'] = url_for('.complete_draft_service', draft_id=self.id)
        data['links']['copy'] = url_for('.copy_draft_service', draft_id=self.id)

        return data

    def get_link(self):
        return url_for(".fetch_draft_service", draft_id=self.id)


class AuditEvent(db.Model):
    __tablename__ = 'audit_event'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String, index=True, nullable=False)
    created_at = db.Column(db.DateTime, index=True, nullable=False, default=datetime.utcnow)
    user = db.Column(db.String)
    data = db.Column(JSON)

    object_type = db.Column(db.String)
    object_id = db.Column(db.BigInteger)

    object = generic_relationship(
        object_type, object_id
    )

    acknowledged = db.Column(
        db.Boolean,
        index=True,
        unique=False,
        nullable=False)

    acknowledged_by = db.Column(db.String)
    acknowledged_at = db.Column(
        db.DateTime,
        nullable=True)

    def __init__(self, audit_type, user, data, db_object):
        self.type = audit_type.value
        self.data = data
        self.object = db_object
        self.user = user
        self.acknowledged = False

    class query_class(BaseQuery):
        def last_for_object(self, object, types=None):
            events = self.filter(AuditEvent.object == object)
            if types is not None:
                events = events.filter(AuditEvent.type.in_(types))

            return events.order_by(desc(AuditEvent.created_at)).first()

    def serialize(self, include_user=False):
        """
        :return: dictionary representation of an audit event
        """

        data = {
            'id': self.id,
            'type': self.type,
            'acknowledged': self.acknowledged,
            'user': self.user,
            'data': self.data,
            'createdAt': self.created_at.strftime(DATETIME_FORMAT),
            'links': filter_null_value_fields({
                "self": url_for(".list_audits"),
                "oldArchivedService": ArchivedService.link_object(
                    self.data.get('oldArchivedServiceId')
                ),
                "newArchivedService": ArchivedService.link_object(
                    self.data.get('newArchivedServiceId')
                )
            })
        }

        if self.acknowledged:
            data.update({
                'acknowledgedAt':
                    self.acknowledged_at.strftime(DATETIME_FORMAT),
                'acknowledgedBy':
                    self.acknowledged_by,
            })

        if include_user:
            user = User.query.filter(
                User.email_address == self.user
            ).first()

            if user:
                data['userName'] = user.name

        return data


class Brief(db.Model):
    __tablename__ = 'brief'

    CLARIFICATION_QUESTIONS_OPEN_DAYS = 7
    CLARIFICATION_QUESTIONS_PUBLISHED_DAYS = 1
    APPLICATIONS_OPEN_DAYS = 14

    id = db.Column(db.Integer, primary_key=True)

    framework_id = db.Column(db.Integer, db.ForeignKey('framework.id'), nullable=False)
    _lot_id = db.Column("lot_id", db.Integer, db.ForeignKey('lot.id'), nullable=False)

    data = db.Column(JSON)
    created_at = db.Column(db.DateTime, index=True, nullable=False,
                           default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, index=True, nullable=False,
                           default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime, index=True, nullable=True)
    withdrawn_at = db.Column(db.DateTime, index=True, nullable=True)

    __table_args__ = (db.ForeignKeyConstraint([framework_id, _lot_id],
                                              ['framework_lot.framework_id', 'framework_lot.lot_id']),
                      {})

    users = db.relationship('User', secondary='brief_user')
    framework = db.relationship('Framework', lazy='joined')
    lot = db.relationship('Lot', lazy='joined')
    clarification_questions = db.relationship(
        "BriefClarificationQuestion",
        order_by="BriefClarificationQuestion.published_at")

    @validates('users')
    def validates_users(self, key, user):
        if user.role != 'buyer':
            raise ValidationError("The brief user must be a buyer")
        return user

    @property
    def lot_id(self):
        return self._lot_id

    @lot_id.setter
    def lot_id(self, lot_id):
        raise ValidationError("Cannot update lot_id directly, use lot relationship")

    @validates('lot')
    def validates_lot(self, key, lot):
        if not lot.allows_brief:
            raise ValidationError("Lot '{}' does not require a brief".format(lot.name))
        return lot

    @validates('data')
    def validates_data(self, key, data):
        data = drop_foreign_fields(data, [
            'id',
            'frameworkSlug', 'frameworkFramework', 'frameworkName', 'frameworkStatus',
            'lot', 'lotSlug', 'lotName',
            'updatedAt', 'createdAt', 'links'
        ])

        data = strip_whitespace_from_data(data)
        data = purge_nulls_from_data(data)

        return data

    @hybrid_property
    def applications_closed_at(self):
        if self.published_at is None:
            return None
        brief_publishing_date_and_length = self._build_date_and_length_data()

        return get_publishing_dates(brief_publishing_date_and_length)['closing_date']

    @applications_closed_at.expression
    def applications_closed_at(cls):
        return sql_case([
            (cls.data['requirementsLength'].astext == '1 week', func.date_trunc('day', cls.published_at) + sql_cast(
                '1 week 23:59:59', INTERVAL)),
            ], else_=func.date_trunc('day', cls.published_at) + sql_cast(
                '2 weeks 23:59:59', INTERVAL))

    @hybrid_property
    def clarification_questions_closed_at(self):
        if self.published_at is None:
            return None
        brief_publishing_date_and_length = self._build_date_and_length_data()

        return get_publishing_dates(brief_publishing_date_and_length)['questions_close']

    @hybrid_property
    def clarification_questions_published_by(self):
        if self.published_at is None:
            return None
        brief_publishing_date_and_length = self._build_date_and_length_data()

        return get_publishing_dates(brief_publishing_date_and_length)['answers_close']

    @hybrid_property
    def clarification_questions_are_closed(self):
        return datetime.utcnow() > self.clarification_questions_closed_at

    @hybrid_property
    def status(self):
        if self.withdrawn_at:
            return 'withdrawn'
        elif not self.published_at:
            return 'draft'
        elif self.applications_closed_at > datetime.utcnow():
            return 'live'
        else:
            return 'closed'

    @status.setter
    def status(self, value):
        if self.status == value:
            return

        if value == 'live' and self.status == 'draft':
            self.published_at = datetime.utcnow()
        elif value == 'withdrawn' and self.status == 'live':
            self.withdrawn_at = datetime.utcnow()
        else:
            raise ValidationError("Cannot change brief status from '{}' to '{}'".format(self.status, value))

    @status.expression
    def status(cls):
        return sql_case([
            (cls.withdrawn_at.isnot(None), 'withdrawn'),
            (cls.published_at.is_(None), 'draft'),
            (cls.applications_closed_at > datetime.utcnow(), 'live')
        ], else_='closed')

    class query_class(BaseQuery):
        def has_statuses(self, *statuses):
            return self.filter(Brief.status.in_(statuses))

    def add_clarification_question(self, question, answer):
        clarification_question = BriefClarificationQuestion(
            brief=self,
            question=question,
            answer=answer,
        )
        clarification_question.validate()

        Session.object_session(self).add(clarification_question)

        return clarification_question

    def update_from_json(self, data):
        current_data = dict(self.data.items())
        current_data.update(data)

        self.data = current_data

    def copy(self):
        if self.framework.status != 'live':
            raise ValidationError("Framework is not live")

        return Brief(
            data=self.data,
            framework=self.framework,
            lot=self.lot,
            users=self.users
        )

    def _build_date_and_length_data(self):
        published_day = self.published_at.replace(hour=23, minute=59, second=59, microsecond=0)
        requirements_length = self.data.get('requirementsLength')

        return {
            'publishedAt': published_day,
            'requirementsLength': requirements_length
        }

    def serialize(self, with_users=False):
        data = dict(self.data.items())

        data.update({
            'id': self.id,
            'status': self.status,
            'frameworkSlug': self.framework.slug,
            'frameworkFramework': self.framework.framework,
            'frameworkName': self.framework.name,
            'frameworkStatus': self.framework.status,
            'lot': self.lot.slug,
            'lotSlug': self.lot.slug,
            'lotName': self.lot.name,
            'createdAt': self.created_at.strftime(DATETIME_FORMAT),
            'updatedAt': self.updated_at.strftime(DATETIME_FORMAT),
            'clarificationQuestions': [
                question.serialize() for question in self.clarification_questions
            ],
        })

        if self.published_at:
            data.update({
                'publishedAt': self.published_at.strftime(DATETIME_FORMAT),
                'applicationsClosedAt': self.applications_closed_at.strftime(DATETIME_FORMAT),
                'clarificationQuestionsClosedAt': self.clarification_questions_closed_at.strftime(DATETIME_FORMAT),
                'clarificationQuestionsPublishedBy': self.clarification_questions_published_by.strftime(
                    DATETIME_FORMAT),
                'clarificationQuestionsAreClosed': self.clarification_questions_are_closed,
            })

        if self.withdrawn_at:
            data.update({
                'withdrawnAt': self.withdrawn_at.strftime(DATETIME_FORMAT)
            })

        data['links'] = {
            'self': url_for('.get_brief', brief_id=self.id),
            'framework': url_for('.get_framework', framework_slug=self.framework.slug),
        }

        if with_users:
            data['users'] = [
                drop_foreign_fields(
                    user.serialize(),
                    ['locked', 'createdAt', 'updatedAt', 'passwordChangedAt', 'loggedInAt', 'failedLoginCount']
                ) for user in self.users
            ]

        return data


class BriefUser(db.Model):
    __tablename__ = 'brief_user'

    brief_id = db.Column(db.Integer, db.ForeignKey('brief.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)


class BriefResponse(db.Model):
    __tablename__ = 'brief_response'

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(JSON, nullable=False)

    brief_id = db.Column(db.Integer, db.ForeignKey('brief.id'), nullable=False)
    supplier_code = db.Column(db.BigInteger, db.ForeignKey('supplier.code'), nullable=False)

    created_at = db.Column(db.DateTime, index=True, nullable=False, default=datetime.utcnow)

    brief = db.relationship('Brief')
    supplier = db.relationship('Supplier', lazy='joined')

    @validates('data')
    def validates_data(self, key, data):
        data = drop_foreign_fields(data, [
            'supplierCode', 'briefId',
        ])
        data = strip_whitespace_from_data(data)
        data = purge_nulls_from_data(data)

        return data

    def validate(self, enforce_required=True, required_fields=None, max_day_rate=None):
        errs = get_validation_errors(
            'brief-responses-{}-{}'.format(self.brief.framework.slug, self.brief.lot.slug),
            self.data,
            enforce_required=enforce_required,
            required_fields=required_fields
        )

        if (
            'essentialRequirements' not in errs and
            len(self.data.get('essentialRequirements', [])) != len(self.brief.data['essentialRequirements'])
        ):
            errs['essentialRequirements'] = 'answer_required'

        if (
            'niceToHaveRequirements' not in errs and
            len(self.data.get('niceToHaveRequirements', [])) != len(self.brief.data.get('niceToHaveRequirements', []))
        ):
            errs['niceToHaveRequirements'] = 'answer_required'

        if max_day_rate and 'dayRate' not in errs:
            if float(self.data['dayRate']) > float(max_day_rate):
                errs['dayRate'] = 'max_less_than_min'

        if errs:
            raise ValidationError(errs)

    def serialize(self):
        data = self.data.copy()
        data.update({
            'id': self.id,
            'briefId': self.brief_id,
            'supplierCode': self.supplier_code,
            'supplierName': self.supplier.name,
            'createdAt': self.created_at.strftime(DATETIME_FORMAT),
            'links': {
                'self': url_for('.get_brief_response', brief_response_id=self.id),
                'brief': url_for('.get_brief', brief_id=self.brief_id),
                'supplier': url_for(".get_supplier", code=self.supplier_code),
            }
        })

        return data


class BriefClarificationQuestion(db.Model):
    __tablename__ = 'brief_clarification_question'

    id = db.Column(db.Integer, primary_key=True)
    _brief_id = db.Column("brief_id", db.Integer, db.ForeignKey("brief.id"), nullable=False)

    question = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)

    published_at = db.Column(db.DateTime, index=True, nullable=False,
                             default=datetime.utcnow)

    brief = db.relationship("Brief")

    @property
    def brief_id(self):
        return self._brief_id

    @validates('question')
    def validates_question(self, key, value):
        return value.strip() if isinstance(value, string_types) else value

    @validates('answer')
    def validates_answer(self, key, value):
        return value.strip() if isinstance(value, string_types) else value

    @brief_id.setter
    def brief_id(self, brief_id):
        raise ValidationError("Cannot update brief_id directly, use brief relationship")

    @validates('brief')
    def validates_brief(self, key, brief):
        if brief.status != "live":
            raise ValidationError("Brief status must be 'live', not '{}'".format(brief.status))
        return brief

    def validate(self):
        data = {"question": self.question, "answer": self.answer}
        data = purge_nulls_from_data(data)
        errs = get_validation_errors("brief-clarification-question", data)

        if errs:
            raise ValidationError(errs)

    def serialize(self):
        return {
            "question": self.question,
            "answer": self.answer,
            "publishedAt": self.published_at.strftime(DATETIME_FORMAT),
        }


# Index for .last_for_object queries. Without a composite index the
# query executes an index backward scan on created_at with filter,
# which takes a long time for old events
# This also replaces the previous (object_type, object_id) index.
db.Index(
    'idx_audit_events_object_and_type',
    AuditEvent.object_type,
    AuditEvent.object_id,
    AuditEvent.type,
    AuditEvent.created_at,
)

# Index for type + acknowledged audit event query count - for admin
# app "Service updates" requests: while the page of audit events
# will rely on the created_at index scan and is relatively quick,
# count(*) query executed by `.paginate` is very slow without a
# dedicated index for objects with multiple events
db.Index(
    'idx_audit_events_type_acknowledged',
    AuditEvent.type,
    AuditEvent.acknowledged,
)


def filter_null_value_fields(obj):
    return dict(
        filter(lambda x: x[1] is not None, obj.items())
    )


def generate_new_service_id(framework_slug):
    # FIXME framework_slug parameter ignored??
    return str(random.randint(10 ** 14, 10 ** 15 - 1))
