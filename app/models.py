import random
from datetime import datetime
from decimal import InvalidOperation
from workdays import workday
import re
import io
import yaml
import six

from flask import current_app
from flask_sqlalchemy import BaseQuery
import flask_featureflags as feature

from six import string_types, text_type, binary_type

from sqlalchemy import text
from sqlalchemy import asc, desc, func, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import validates, relationship
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import case as sql_case
from sqlalchemy.sql.expression import cast as sql_cast
from sqlalchemy.types import String, Date, Integer, Interval
from sqlalchemy_utils import generic_relationship
from sqlalchemy.schema import Sequence
from dmutils.data_tools import ValidationError, normalise_abn, normalise_acn, parse_money
from dmapiclient.audit import AuditTypes

from . import db

from app.utils import (
    link, url_for, strip_whitespace_from_data, drop_foreign_fields, purge_nulls_from_data, filter_fields
)
from .validation import is_valid_service_id, get_validation_errors, get_validator

from dmutils.forms import is_government_email

from .datetime_utils import DateTime, utcnow, parse_interval, is_textual, \
    parse_time_of_day, combine_date_and_time, localnow, utcnow

import pendulum

from functools import partial

from .jiraapi import get_marketplace_jira
from .modelsbase import normalize_key_case
from .utils import sorted_uniques, log


with io.open('data/domain_mapping_old_to_new.yaml') as f:
    DOMAIN_MAPPING = yaml.load(f.read())


with io.open('data/specialist_role_old_to_new.yaml') as f:
    DOMAIN_MAPPING_SPECIALISTS = yaml.load(f.read())


class Agency(db.Model):
    __tablename__ = 'agency'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    domain = db.Column(db.String, nullable=False, unique=True, index=True)
    category = db.Column(db.String)
    state = db.Column(db.String)


class Council(db.Model):
    __tablename__ = 'council'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    domain = db.Column(db.String, nullable=False, unique=True, index=True)
    home_page = db.Column(db.String)


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
    data = db.Column(MutableDict.as_mutable(JSON))

    @property
    def allows_brief(self):
        return self.one_service_limit

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
    name = db.Column(db.String, nullable=False)
    framework = db.Column(db.String, index=True, nullable=False)
    framework_agreement_details = db.Column(JSON, nullable=True)
    status = db.Column(db.String,
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
        except KeyError as e:
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
    postal_code = db.Column(db.String, index=False, nullable=False)
    country = db.Column(db.String, index=False, nullable=False, default='Australia')

    supplier_code = db.Column(db.BigInteger, db.ForeignKey('supplier.code'), nullable=True)
    supplier = db.relationship('Supplier', lazy='joined')

    @staticmethod
    def from_json(as_dict):
        if 'links' in as_dict:
            del as_dict['links']

        return Address(**as_dict)

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
        as_dict = normalize_key_case(as_dict)

        try:
            return Contact(contact_for=as_dict.get('contact_for', None),
                           name=as_dict.get('name'),
                           role=as_dict.get('role', None),
                           email=as_dict.get('email', None),
                           phone=as_dict.get('phone', None),
                           fax=as_dict.get('fax', None))
        except KeyError as e:
            raise ValidationError('Contact missing required field: {}'.format(e))

    def serializable_after(self, data):
        data['contactFor'] = data['contact_for']
        return data

    def serialize(self):
        serialized = {
            'contactFor': self.contact_for,
            'contact_for': self.contact_for,
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
            s = SupplierReference()
            s.update_from_json(as_dict)
            return s
        except KeyError as e:
            raise ValidationError('Supplier reference missing required field: {}'.format(e))

    def serialize(self):
        return s.json


class ServiceCategory(db.Model):
    __tablename__ = 'service_category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    abbreviation = db.Column(db.String, nullable=False)

    @staticmethod
    def lookup(as_dict):
        name = as_dict.get('name', 'no category specified')
        result = ServiceCategory.query.filter_by(name=name).first()
        if result is None:
            raise ValidationError('Unknown category: {}'.format(name))
        return result

    def serialize(self):
        return s.json

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
    abbreviation = db.Column(db.String, nullable=False)

    @staticmethod
    def lookup(as_dict):
        category_name = as_dict.get('category', 'no category specified')
        ServiceCategory.lookup({'name': category_name})
        role_name = as_dict.get('role', 'no role specified')
        result = ServiceRole.query.filter_by(name=role_name).first()
        if result is None:
            raise ValidationError('Unknown role: {}'.format(role_name))
        return result

    @staticmethod
    def lookupbyrolename(role_name):
        result = ServiceRole.query.filter_by(name=role_name).first()
        if result is None:
            raise ValidationError('Unknown role: {}'.format(role_name))
        return result

    def serializable_after(self, data):
        data['category'] = self.category.name
        data['role'] = self.name
        return data

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
        except KeyError as e:
            raise ValidationError('Price schedule missing required field: {}'.format(e))
        except InvalidOperation as e:
            raise ValidationError('Invalid rate value: {}'.format(e))

    @staticmethod
    def from_submitted_pricing_json(as_dict):
        def it():
            for k, v in as_dict.iteritems():
                for level in ['Junior', 'Senior']:
                    if level == 'Junior':
                        price_field = 'minPrice'
                    elif level == 'Senior':
                        price_field = 'maxPrice'

                    rolename = '{} {}'.format(level, k)
                    service_role = ServiceRole.lookupbyrolename(rolename)
                    hourly_rate = v[price_field]
                    yield PriceSchedule(service_role=service_role, hourly_rate=hourly_rate)
        return list(it())

    def serializable_after(self, data):
        data['dailyRate'] = data.get('daily_rate', None)
        data['hourlyRate'] = data.get('hourly_rate', None)
        data['serviceRole'] = data.get('service_role', None)
        data['gstIncluded'] = data.get('gst_included', None)
        return data

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
        if is_textual(rate):
            return parse_money(rate)
        return rate


class Agreement(db.Model):
    __tablename__ = 'agreement'

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String, unique=True, nullable=False)
    url = db.Column(db.String, nullable=False)
    is_current = db.Column(db.Boolean, nullable=True)


class SignedAgreement(db.Model):
    __tablename__ = 'signed_agreement'

    agreement_id = db.Column(
        db.Integer,
        db.ForeignKey('agreement.id', ondelete='cascade'),
        primary_key=True,
        nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='cascade'),
        primary_key=True,
        nullable=False
    )
    application_id = db.Column(
        db.Integer,
        db.ForeignKey('application.id', ondelete='cascade'),
        primary_key=True,
        nullable=False
    )

    signed_at = db.Column(
        DateTime,
        primary_key=True,
        index=False,
        unique=False,
        nullable=False)


class SupplierExtraLinks(db.Model):
    __tablename__ = 'supplier__extra_links'
    supplier_id = db.Column(
        db.Integer,
        db.ForeignKey('supplier.id', ondelete='cascade'),
        primary_key=True,
        nullable=False
    )
    website_link_id = db.Column(db.Integer, db.ForeignKey('website_link.id'), primary_key=True, nullable=False)


class SupplierContact(db.Model):
    __tablename__ = 'supplier__contact'
    supplier_id = db.Column(
        db.Integer,
        db.ForeignKey('supplier.id', ondelete='cascade'),
        primary_key=True,
        nullable=False
    )
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), primary_key=True, nullable=False)


supplier_domain_id_seq = Sequence('supplier_domain_id_seq')


class SupplierDomain(db.Model):
    __tablename__ = 'supplier_domain'

    id = db.Column(
        db.Integer,
        supplier_domain_id_seq,
        server_default=supplier_domain_id_seq.next_value(),
        index=True,
        unique=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'), primary_key=True)
    recruiter_info_id = db.Column(db.Integer, db.ForeignKey('recruiter_info.id'))

    domain = relationship("Domain", back_populates="suppliers")
    supplier = relationship("Supplier", back_populates="domains")

    recruiter_info = relationship("RecruiterInfo", back_populates="suppliers")

    status = db.Column(
        db.Enum(
            *[
                'unassessed',
                'assessed',
                'rejected'
            ],
            name='supplier_domain_status_enum'
        ),
        default='unassessed',
        index=False,
        unique=False,
        nullable=False
    )


supplier_code_seq = Sequence('supplier_code_seq')


class Supplier(db.Model):
    EXCLUDE_FOR_SERIALIZATION = [
        'work_orders',
        'applications',
        'brief_responses']

    DUMMY_ABN = '50 110 219 460'

    __tablename__ = 'supplier'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(
        db.BigInteger,
        supplier_code_seq,
        index=True,
        unique=True,
        nullable=False,
        server_default=supplier_code_seq.next_value())
    name = db.Column(db.String, nullable=False)
    long_name = db.Column(db.String, nullable=True)
    summary = db.Column(db.String, index=False, nullable=True)
    description = db.Column(db.String, index=False, nullable=True)
    addresses = db.relationship('Address', single_parent=True, cascade='all, delete-orphan')
    website = db.Column(db.String, index=False, nullable=True)
    linkedin = db.Column(db.String, index=False, nullable=True)
    extra_links = db.relationship('WebsiteLink',
                                  secondary=SupplierExtraLinks.__table__,
                                  single_parent=True,
                                  cascade='all, delete-orphan')
    abn = db.Column(db.String, nullable=True)
    acn = db.Column(db.String, nullable=True)
    contacts = db.relationship(
        'Contact',
        secondary=SupplierContact.__table__,
        single_parent=True,
        cascade='all, delete-orphan'
    )
    case_studies = db.relationship('CaseStudy', single_parent=True, cascade='all, delete-orphan')
    work_orders = db.relationship('WorkOrder', single_parent=True, cascade='all, delete-orphan')
    applications = db.relationship('Application', single_parent=True, cascade='all, delete-orphan')
    brief_responses = db.relationship('BriefResponse', single_parent=True, cascade='all, delete-orphan')
    products = db.relationship('Product', single_parent=True, cascade='all, delete-orphan')
    references = db.relationship('SupplierReference', single_parent=True, cascade='all, delete-orphan')
    prices = db.relationship('PriceSchedule', single_parent=True, cascade='all, delete-orphan')
    status = db.Column(
        db.Enum(
            *[
                'limited',
                'complete',
                'deleted'
            ],
            name='supplier_status_enum'
        ),
        default='complete',
        index=False,
        unique=False,
        nullable=False
    )
    is_recruiter = db.Column(db.String, nullable=False, default=False, server_default=text('false'))
    data = db.Column(MutableDict.as_mutable(JSON), default=dict)

    # TODO: migrate these to plain (non-timezone) fields
    creation_time = db.Column(DateTime(timezone=True),
                              index=False,
                              nullable=False,
                              default=localnow)

    last_update_time = db.Column(DateTime(timezone=True),
                                 index=False,
                                 nullable=False,
                                 default=localnow)

    domains = relationship("SupplierDomain", back_populates="supplier")
    frameworks = relationship("SupplierFramework")

    def add_unassessed_domain(self, name_or_id):
        d = Domain.get_by_name_or_id(name_or_id)
        sd = SupplierDomain(supplier=self, domain=d, status='unassessed')
        db.session.add(sd)
        db.session.add(AuditEvent(
            audit_type=AuditTypes.unassessed_domain,
            user='',
            data={},
            db_object=sd
        ))
        db.session.flush()

    def update_domain_assessment_status(self, name_or_id, status):
        d = Domain.get_by_name_or_id(name_or_id)

        sd = SupplierDomain.query.filter_by(supplier_id=self.id, domain_id=d.id).first()

        if not sd:
            raise ValidationError('no domain assessment exists for: {}'.format(name))

        sd.status = status
        if status == 'assessed':
            db.session.add(AuditEvent(
                audit_type=AuditTypes.assessed_domain,
                user='',
                data={},
                db_object=sd
            ))
        db.session.flush()

    @property
    def all_domains(self):
        new_domains = [sd.domain.name for sd in self.domains]
        result = new_domains + self.legacy_domains
        return sorted_uniques(result)

    @property
    def assessed_domains(self):
        approved_new_domains = [sd.domain.name for sd in self.domains if sd.status == 'assessed']
        result = approved_new_domains + self.legacy_domains
        return sorted_uniques(result)

    @property
    def unassessed_domains(self):
        result = [sd.domain.name for sd in self.domains if not sd.status == 'assessed']
        return sorted_uniques(result)

    @property
    def legacy_domains(self):
        def map_legacy_to_new(legacy_name):
            n = legacy_name

            PREFIX = ['Senior ', 'Junior ']

            for pre in PREFIX:
                if legacy_name.startswith(pre):
                    n = n[len(pre):]

            try:
                return DOMAIN_MAPPING[n]
            except KeyError:
                raise ValueError('invalid legacy domain')

        legacy_domains = [
            map_legacy_to_new(p.service_role.name)
            for p in self.prices
        ]

        return sorted_uniques(legacy_domains)

    def get_service_counts(self):
        # FIXME: To be removed from Australian version
        return {}

    def get_link(self):
        return url_for(".get_supplier", code=self.code)

    # TODO: address.serializable hits recursion limit
    def serialize_address(self, address):
        return {
            'address_line': address.address_line,
            'suburb': address.suburb,
            'state': address.state,
            'postal_code': address.postal_code,
            'country': address.country
        }

    def serializable_after(self, j):
        legacy = {
            'longName': self.long_name,
            'extraLinks': [l.serialize() for l in self.extra_links],
            'case_study_ids': [c.id for c in self.case_studies],
            'creationTime': self.creation_time,
            'lastUpdateTime': self.last_update_time,
            'supplierCode': self.code
        }
        j.update(legacy)

        j['domains'] = {
            'assessed': self.assessed_domains,
            'unassessed': self.unassessed_domains,
            'legacy': self.legacy_domains
        }

        j['services'] = {
            d: True for d in self.assessed_domains
        }

        def without_id(dictionary):
            d = dict(dictionary)
            del d['id']
            return d

        j['recruiter_info'] = {
            d.domain.name: without_id(d.recruiter_info._fieldsdict)
            for d in self.domains if d.recruiter_info
        }

        if self.contacts:
            contact = self.contacts[0]
            j['representative'] = contact.name
            j['email'] = contact.email
            j['phone'] = contact.phone

        if self.addresses:
            j['address'] = self.serialize_address(self.addresses[0])

        return j

    def update_from_json_before(self, data):
        self.data = self.data or {}

        if 'abn' in data:
            self.abn = data.pop('abn')

        if 'longName' in data:
            self.long_name = data['longName']

        if 'extraLinks' in data:
            self.extra_links = [WebsiteLink.from_json(l) for l in data['extraLinks']]

        if 'recruiter' in data:
            self.is_recruiter = data['recruiter'].lower() in ('yes', 'true')
            del data['recruiter']

        if 'representative' in data:
            self.contacts = [
                Contact.from_json(c) for c in [{
                    'name': data.get('representative'),
                    'email': data.get('email'),
                    'phone': data.get('phone')
                }]
            ]

        overridden = [
            'longName',
            'extraLinks',
        ]

        for k in overridden:
            if k in data:
                del data[k]

        return data

    def update_from_json_after(self, data):
        self.last_update_time = utcnow()

        if 'services' in self.data:
            for name, checked in self.data['services'].items():
                if name not in self.all_domains and checked:
                    self.add_unassessed_domain(name)
            del self.data['services']

        if 'seller_types' in self.data:
            self.data['seller_types']['recruitment'] = self.is_recruiter
        else:
            self.data['seller_types'] = {'recruitment': self.is_recruiter}

        if 'recruiter_info' in self.data:
            for d in self.domains:
                if d.domain.name in self.data['recruiter_info']:
                    info = self.data['recruiter_info'][d.domain.name]
                    d.recruiter_info = RecruiterInfo(**info)
            del self.data['recruiter_info']

        return data

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


class Domain(db.Model):
    __tablename__ = 'domain'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    ordering = db.Column(db.Integer, nullable=False)

    suppliers = relationship("SupplierDomain", back_populates="domain")
    assoc_suppliers = association_proxy('suppliers', 'supplier')

    @staticmethod
    def get_by_name_or_id(name_or_id):
        if isinstance(name_or_id, six.string_types):
            d = Domain.query.filter(
                func.lower(Domain.name) == func.lower(name_or_id)
            ).first()
        else:
            d = Domain.query.filter_by(id=name_or_id).first()

        if not d:
            raise ValidationError('cannot find domain: {}'.format(name_or_id))
        return d


class RecruiterInfo(db.Model):
    __tablename__ = 'recruiter_info'
    id = db.Column(db.Integer, primary_key=True)
    active_candidates = db.Column(db.String, nullable=False)
    database_size = db.Column(db.String, nullable=False)
    placed_candidates = db.Column(db.String, nullable=False)
    margin = db.Column(db.String, nullable=False)
    markup = db.Column(db.String, nullable=False)

    suppliers = relationship("SupplierDomain", back_populates="recruiter_info")
    assoc_suppliers = association_proxy('suppliers', 'supplier')


class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    pricing = db.Column(db.String)
    summary = db.Column(db.String)
    support = db.Column(db.String)
    website = db.Column(db.String)

    supplier_code = db.Column(db.BigInteger, db.ForeignKey('supplier.code'), nullable=False)

    supplier = db.relationship('Supplier', lazy='select', innerjoin=True)

    @staticmethod
    def get_by_name_or_id(name_or_id):
        if isinstance(name_or_id, six.string_types):
            d = Product.query.filter(
                func.lower(Product.name) == func.lower(name_or_id)
            ).first()
        else:
            d = Product.query.filter_by(id=name_or_id).first()

        if not d:
            raise ValidationError('cannot find product: {}'.format(name_or_id))
        return d

    @staticmethod
    def from_json(data):
        return Product(**data)


class SupplierFramework(db.Model):
    __tablename__ = 'supplier_framework'

    supplier_code = db.Column(db.BigInteger,
                              db.ForeignKey('supplier.code'),
                              primary_key=True)
    framework_id = db.Column(db.Integer,
                             db.ForeignKey('framework.id'),
                             primary_key=True)
    declaration = db.Column(MutableDict.as_mutable(JSON))
    on_framework = db.Column(db.Boolean, nullable=True)
    agreement_returned_at = db.Column(DateTime, index=False, unique=False, nullable=True)
    countersigned_at = db.Column(DateTime, index=False, unique=False, nullable=True)
    agreement_details = db.Column(MutableDict.as_mutable(JSON))

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
            agreement_returned_at = agreement_returned_at.to_iso8601_string(extended=True)

        countersigned_at = self.countersigned_at
        if countersigned_at:
            countersigned_at = countersigned_at.to_iso8601_string(extended=True)

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
        'applicant'
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

    created_at = db.Column(DateTime, index=False, unique=False,
                           nullable=False, default=utcnow)
    updated_at = db.Column(DateTime, index=False, unique=False,
                           nullable=False, default=utcnow,
                           onupdate=utcnow)
    password_changed_at = db.Column(DateTime, index=False, unique=False,
                                    nullable=False)
    logged_in_at = db.Column(DateTime, nullable=True)
    terms_accepted_at = db.Column(DateTime, index=False, nullable=False, default=utcnow)

    # used to determine whether account is `locked`. field is reset upon successful login or can
    # be reset manually to "unlock" an account.
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)

    # used by frontends to determine whether view access should be allowed
    role = db.Column(db.Enum(*ROLES, name='user_roles_enum'), index=False, unique=False, nullable=False)

    # FIXME: should be a many-to-many
    supplier_code = db.Column(db.BigInteger,
                              db.ForeignKey('supplier.code', ondelete='cascade'),
                              index=True, unique=False, nullable=True)

    supplier = db.relationship(Supplier, lazy='joined', innerjoin=False)

    application_id = db.Column(db.BigInteger,
                               db.ForeignKey('application.id', ondelete='cascade'),
                               index=True, unique=False, nullable=True)

    application = db.relationship('Application', lazy='joined', innerjoin=False)

    @validates('email_address')
    def validate_email_address(self, key, value):
        if value and self.role == 'buyer' and not is_government_email(value):
            raise ValidationError("invalid_buyer_domain")
        return value

    @validates('role')
    def validate_role(self, key, value):
        if self.email_address and value == 'buyer' and not is_government_email(self.email_address):
            raise ValidationError("invalid_buyer_domain")
        return value

    @validates('created_at', 'updated_at', 'password_changed_at', 'logged_in_at', 'terms_accepted_at')
    def validate_date(self, key, value):
        if value is None or isinstance(value, datetime):
            return value
        try:
            date = pendulum.parse(value)
            return date
        except Exception as e:
            try:
                msg = e.message
            except AttributeError:
                msg = str(e)
            raise ValidationError('Invalid date for {}: {} - {}'.format(key, value, msg))

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

    def serializable_after(self, j):
        del j['password']

        legacy = {
            'emailAddress': self.email_address,
            'phoneNumber': self.phone_number,
            'createdAt': self.created_at,
            'updatedAt': self.updated_at,
            'passwordChangedAt':
                self.password_changed_at,
            'loggedInAt': self.logged_in_at
                if self.logged_in_at else None,
            'termsAcceptedAt': self.terms_accepted_at,
            'failedLoginCount': self.failed_login_count,
            'locked': self.locked
        }
        j.update(legacy)
        return j

    def serialize(self):
        return self.serializable

    def viewrow(self):
        select = db.session.execute("""
            select * from "vuser" where id = :id
        """, {'id': self.id})
        return list(select)[0]


class SupplierUserInviteLog(db.Model):
    __tablename__ = 'supplier_user_invite_log'

    supplier_id = db.Column(
        db.Integer,
        db.ForeignKey('supplier.id', ondelete='cascade'),
        primary_key=True,
        nullable=False
    )
    contact_id = db.Column(
        db.Integer,
        db.ForeignKey('contact.id', ondelete='cascade'),
        primary_key=True,
        nullable=False
    )
    invite_sent = db.Column(DateTime, index=True, nullable=False, default=utcnow)
    __table_args__ = (
        db.ForeignKeyConstraint(
            ('supplier_id', 'contact_id'),
            ('supplier__contact.supplier_id', 'supplier__contact.contact_id'),
            ondelete='cascade',
        ),
    )


class ServiceTableMixin(object):
    STATUSES = ('disabled', 'enabled', 'published')

    # not used as the externally-visible "pk" by actual Services in favour of service_id
    id = db.Column(db.Integer, primary_key=True)

    # used as externally-visible "pk" for Services and allows services identity to be tracked
    # across a service's lifetime. assigned randomly (see generate_new_service_id) at DraftService ->
    # Service publishing time.
    service_id = db.Column(db.String, index=True, unique=True, nullable=False)

    data = db.Column(MutableDict.as_mutable(JSON))
    status = db.Column(db.String, index=False, unique=False, nullable=False)

    created_at = db.Column(DateTime, index=False, nullable=False,
                           default=utcnow)
    updated_at = db.Column(DateTime, index=False, nullable=False,
                           default=utcnow, onupdate=utcnow)

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

    def update_from_json(self, data):
        current_data = dict(self.data.items())
        current_data.update(data)

        self.data = current_data

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
            'updatedAt': self.updated_at.to_iso8601_string(extended=True),
            'createdAt': self.created_at.to_iso8601_string(extended=True),
            'status': self.status
        })

        data['links'] = link(
            "self", self.get_link()
        )

        return data

    ADDITIONAL_REPR_FIELDS = ['service_id', 'supplier_code', 'lot']


class Service(ServiceTableMixin, db.Model):
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


class ArchivedService(ServiceTableMixin, db.Model):
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


class DraftService(ServiceTableMixin, db.Model):
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
    created_at = db.Column(DateTime, index=True, nullable=False, default=utcnow)
    user = db.Column(db.String)
    data = db.Column(MutableDict.as_mutable(JSON), default=dict)

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
        DateTime,
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
            'createdAt': self.created_at.to_iso8601_string(extended=True),
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
                    self.acknowledged_at.to_iso8601_string(extended=True),
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

    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'), nullable=True)

    data = db.Column(MutableDict.as_mutable(JSON))
    created_at = db.Column(DateTime, index=True, nullable=False,
                           default=utcnow)
    updated_at = db.Column(DateTime, index=True, nullable=False,
                           default=utcnow, onupdate=utcnow)
    published_at = db.Column(DateTime, index=True, nullable=True)
    withdrawn_at = db.Column(DateTime, index=True, nullable=True)

    __table_args__ = (db.ForeignKeyConstraint([framework_id, _lot_id],
                                              ['framework_lot.framework_id', 'framework_lot.lot_id']),
                      {})

    users = db.relationship('User', secondary='brief_user')
    framework = db.relationship('Framework', lazy='joined')
    lot = db.relationship('Lot', lazy='joined')
    clarification_questions = db.relationship(
        "BriefClarificationQuestion",
        order_by="BriefClarificationQuestion.published_at")
    work_order = db.relationship('WorkOrder', uselist=False)
    domain = db.relationship('Domain', lazy='joined')

    @property
    def domain(self):
        specialist_role = self.data.get('specialistRole')

        if not specialist_role:
            return None

        name = DOMAIN_MAPPING_SPECIALISTS[specialist_role]
        return Domain.get_by_name_or_id(name)

    @property
    def dates_for_serialization(self):
        def as_s(x):
            if x:
                return str(x)

        def stringified(d):
            return {k: as_s(v) for k, v in d.items()}

        dates = {}

        dates['published_date'] = self.published_day
        dates['closing_date'] = self.applications_closing_date
        dates['questions_close'] = self.clarification_questions_closed_at
        dates['answers_close'] = self.clarification_questions_published_by
        dates['application_open_weeks'] = self.requirements_length
        dates['closing_time'] = self.applications_closed_at

        dates = stringified(dates)

        if not self.published_at:
            published_at = self.published_at
            self.published_at = pendulum.now('UTC')
            dates['hypothetical'] = self.dates_for_serialization
            self.published_at = published_at

        return dates

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
    def published_day(self):
        DEADLINES_TZ_NAME = current_app.config['DEADLINES_TZ_NAME']

        if not self.published_at:
            return None

        local_dt = self.published_at.in_timezone(DEADLINES_TZ_NAME)
        return local_dt.date()

    @published_day.expression
    def published_day(cls):
        DEADLINES_TZ_NAME = current_app.config['DEADLINES_TZ_NAME']

        p_at_utc = cls.published_at.op('at time zone')('UTC')

        p_at_local = p_at_utc.op('at time zone')(DEADLINES_TZ_NAME)

        return sql_case(
            [(cls.published_at.is_(None), None)],
            else_=sql_cast(p_at_local, Date)
        )

    @hybrid_property
    def requirements_length(self):
        DEFAULT_REQUIREMENTS_DURATION = current_app.config['DEFAULT_REQUIREMENTS_DURATION']
        return self.data.get(
            'requirementsLength',
            DEFAULT_REQUIREMENTS_DURATION)

    @requirements_length.expression
    def requirements_length(cls):
        DEFAULT_REQUIREMENTS_DURATION = current_app.config['DEFAULT_REQUIREMENTS_DURATION']
        return func.coalesce(
            cls.data.op('->>')('requirementsLength'),
            DEFAULT_REQUIREMENTS_DURATION)

    @property
    def questions_duration_workdays(self):
        if self.requirements_length == '1 week':
            return 2
        else:
            return 5

    @property
    def applications_closing_date(self):
        if self.published_at is None:
            return None
        req_length = parse_interval(self.requirements_length)
        return self.published_day + req_length

    @hybrid_property
    def hypothetical_applications_closed_at(self):
        DEADLINES_TZ_NAME = current_app.config['DEADLINES_TZ_NAME']
        DEADLINES_TIME_OF_DAY = current_app.config['DEADLINES_TIME_OF_DAY']

        if self.published_at is not None:
            return None
        d = pendulum.now(DEADLINES_TZ_NAME).date() + \
            parse_interval(self.requirements_length)
        t = parse_time_of_day(DEADLINES_TIME_OF_DAY)
        combined = combine_date_and_time(d, t, DEADLINES_TZ_NAME)
        return combined.in_timezone('UTC')

    @hybrid_property
    def applications_closed_at(self):
        DEADLINES_TZ_NAME = current_app.config['DEADLINES_TZ_NAME']
        DEADLINES_TIME_OF_DAY = current_app.config['DEADLINES_TIME_OF_DAY']

        if self.published_at is None:
            return None
        d = self.applications_closing_date
        t = parse_time_of_day(DEADLINES_TIME_OF_DAY)
        combined = combine_date_and_time(d, t, DEADLINES_TZ_NAME)
        return combined.in_timezone('UTC')

    @applications_closed_at.expression
    def applications_closed_at(cls):
        DEADLINES_TZ_NAME = current_app.config['DEADLINES_TZ_NAME']
        DEADLINES_TIME_OF_DAY = current_app.config['DEADLINES_TIME_OF_DAY']
        t = parse_time_of_day(DEADLINES_TIME_OF_DAY)

        req_interval = sql_cast(cls.requirements_length, Interval)
        day_count = sql_cast(func.extract('days', req_interval), Integer)
        closing_day = cls.published_day + day_count
        naive_deadline = func._(closing_day + t)
        local_deadline = naive_deadline.op('at time zone')(DEADLINES_TZ_NAME)
        utc_deadline = local_deadline.op('at time zone')('UTC')

        return sql_case(
            [(cls.published_at.is_(None), None)],
            else_=utc_deadline
        )

    @property
    def clarification_questions_closed_at(self):
        if self.published_at is None:
            return None
        DEADLINES_TIME_OF_DAY = current_app.config['DEADLINES_TIME_OF_DAY']
        DEADLINES_TZ_NAME = current_app.config['DEADLINES_TZ_NAME']

        if self.published_at is None:
            return None
        d = workday(self.published_day, self.questions_duration_workdays)

        t = parse_time_of_day(DEADLINES_TIME_OF_DAY)
        return combine_date_and_time(d, t, DEADLINES_TZ_NAME).in_tz('UTC')

    @property
    def clarification_questions_published_by(self):
        if self.published_at is None:
            return None

        DEADLINES_TIME_OF_DAY = current_app.config['DEADLINES_TIME_OF_DAY']
        DEADLINES_TZ_NAME = current_app.config['DEADLINES_TZ_NAME']

        d = workday(self.applications_closing_date, -1)

        t = parse_time_of_day(DEADLINES_TIME_OF_DAY)
        return combine_date_and_time(d, t, DEADLINES_TZ_NAME).in_tz('UTC')

    @property
    def clarification_questions_are_closed(self):
        return utcnow() > self.clarification_questions_closed_at

    @hybrid_property
    def status(self):
        if self.withdrawn_at:
            return 'withdrawn'
        elif not self.published_at:
            return 'draft'
        elif self.applications_closed_at > utcnow():
            return 'live'
        else:
            return 'closed'

    @status.setter
    def status(self, value):
        if self.status == value:
            return

        if value == 'live' and self.status == 'draft':
            self.published_at = utcnow()
        elif value == 'withdrawn' and self.status == 'live':
            self.withdrawn_at = utcnow()
        else:
            raise ValidationError("Cannot change brief status from '{}' to '{}'".format(self.status, value))

    @status.expression
    def status(cls):
        return sql_case([
            (cls.withdrawn_at.isnot(None), 'withdrawn'),
            (cls.published_at.is_(None), 'draft'),
            (cls.applications_closed_at > utcnow(), 'live')
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
            'createdAt': self.created_at.to_iso8601_string(extended=True),
            'updatedAt': self.updated_at.to_iso8601_string(extended=True),
            'clarificationQuestions': [
                question.serialize() for question in self.clarification_questions
            ],
        })

        if self.work_order:
            data.update({
                'work_order_id': self.work_order.id,
            })

        if self.published_at:
            data.update({
                'publishedAt': self.published_at.to_iso8601_string(extended=True),
                'applicationsClosedAt': self.applications_closed_at.to_iso8601_string(extended=True),
                'clarificationQuestionsClosedAt':
                    self.clarification_questions_closed_at.to_iso8601_string(extended=True),
                'clarificationQuestionsPublishedBy':
                    self.clarification_questions_published_by.to_iso8601_string(extended=True),
                'clarificationQuestionsAreClosed': self.clarification_questions_are_closed,
            })

        if self.withdrawn_at:
            data.update({
                'withdrawnAt': self.withdrawn_at.to_iso8601_string(extended=True)
            })

        data['links'] = {
            'self': url_for('.get_brief', brief_id=self.id),
            'framework': url_for('.get_framework', framework_slug=self.framework.slug),
        }

        if with_users:
            data['users'] = [
                filter_fields(user.serialize(), ('id', 'emailAddress', 'phoneNumber', 'name', 'role', 'active'))
                for user in self.users
            ]

        data['dates'] = self.dates_for_serialization
        return data

    def serializable_after(self, data):
        data['dates'] = self.dates_for_serialization
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

    created_at = db.Column(DateTime, index=True, nullable=False, default=utcnow)

    brief = db.relationship('Brief')
    supplier = db.relationship('Supplier', lazy='joined')

    @validates('data')
    def validates_data(self, key, data):
        data = drop_foreign_fields(data, [
            'supplierCode', 'briefId',
        ])

        NTF = 'niceToHaveRequirements'
        excluded_keys = [NTF]
        excluded = dict()

        for k in excluded_keys:
            if k in data:
                excluded[k] = data.pop(NTF)

        data = strip_whitespace_from_data(data)

        data.update(excluded)

        data = purge_nulls_from_data(data)

        return data

    def validate(self, enforce_required=True, required_fields=None, max_day_rate=None):
        def clean_non_strings():
            # short term hacky fix for frontend yaml-parsing bug

            def to_text(x):
                if isinstance(x, binary_type):
                    return x.decode('utf-8')
                else:
                    return text_type(x)

            def clean(answers):
                return [to_text(x) for x in answers]

            try:
                self.data['essentialRequirements'] = \
                    clean(self.data['essentialRequirements'])
            except KeyError:
                pass

            try:
                self.data['niceToHaveRequirements'] = \
                    clean(self.data['niceToHaveRequirements'])
            except KeyError:
                pass

        try:
            clean_non_strings()
        except TypeError:
            pass

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
            'createdAt': self.created_at.to_iso8601_string(extended=True),
            'links': {
                'self': url_for('.get_brief_response', brief_response_id=self.id),
                'brief': url_for('.get_brief', brief_id=self.brief_id),
                'supplier': url_for(".get_supplier", code=self.supplier_code),
            }
        })

        return data

    def create_just_in_time_assessment_tasks(self):
        supplier = self.supplier
        assessed_domains = supplier.assessed_domains

        if assessed_domains:
            return

        if current_app.config['JIRA_FEATURES'] and \
                current_app.config['JUST_IN_TIME_ASSESSMENTS']:

            mj = get_marketplace_jira()

            domain = self.brief.domain

            if domain:
                # brief has an associated domain, assess this one
                domains = [domain]
            else:
                # create assessment task for each domain
                domains = [
                    Domain.get_by_name_or_id(name)
                    for name
                    in supplier.unassessed_domains
                ]

            mj.create_supplier_domain_assessment_task(
                supplier,
                domains)


class BriefClarificationQuestion(db.Model):
    __tablename__ = 'brief_clarification_question'

    id = db.Column(db.Integer, primary_key=True)
    _brief_id = db.Column("brief_id", db.Integer, db.ForeignKey("brief.id"), nullable=False)

    question = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)

    published_at = db.Column(DateTime, index=True, nullable=False,
                             default=utcnow)

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
            "publishedAt": self.published_at.to_iso8601_string(extended=True),
        }


class WorkOrder(db.Model):
    __tablename__ = 'work_order'

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(JSON, nullable=False)

    brief_id = db.Column(db.Integer, db.ForeignKey('brief.id'), nullable=False, unique=True)
    supplier_code = db.Column(db.BigInteger, db.ForeignKey('supplier.code'), nullable=False)

    created_at = db.Column(DateTime, index=True, nullable=False, default=utcnow)

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

    def serialize(self):
        data = self.data.copy()
        data.update({
            'id': self.id,
            'briefId': self.brief_id,
            'supplierCode': self.supplier_code,
            'supplierName': self.supplier.name,
            'createdAt': self.created_at.to_iso8601_string(extended=True),
            'links': {
                'self': url_for('.get_work_order', work_order_id=self.id),
                'brief': url_for('.get_brief', brief_id=self.brief_id),
                'supplier': url_for(".get_supplier", code=self.supplier_code),
            }
        })

        return data

    def update_from_json(self, data):
        # Need this juggling because of the validates_data hook
        new_data = dict(self.data)
        new_data.update(data)
        self.data = new_data


class Application(db.Model):
    __tablename__ = 'application'

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(MutableDict.as_mutable(JSON), default=dict, nullable=False)
    created_at = db.Column(DateTime, index=True, nullable=False, default=utcnow)

    status = db.Column(
        db.Enum(
            *[
                'saved',
                'submitted',
                'approved',
                'complete',
                'approval_rejected',
                'assessment_rejected',
                'deleted'
            ],
            name='application_status_enum'
        ),
        default='saved',
        index=True,
        unique=False,
        nullable=False
    )

    supplier_code = db.Column(db.BigInteger,
                              db.ForeignKey('supplier.code'),
                              nullable=True)

    supplier = db.relationship(Supplier, lazy='joined', innerjoin=False)

    @validates('data')
    def validates_data(self, key, data):
        data = strip_whitespace_from_data(data)
        data = purge_nulls_from_data(data)

        return data

    def serializable_after(self, data):
        if 'created_at' in data:
            data['createdAt'] = data['created_at']

        data['signed_agreements'] = self.signed_agreements()

        if self.supplier:
            data['assessed_domains'] = self.supplier.assessed_domains

        return data

    def update_from_json_before(self, data):
        try:
            self.status = data['status']
        except KeyError:
            pass

        try:
            self.supplier_code = data['code']
        except KeyError:
            pass

        get_validator('application').validate(data)

        return data

    def serialize(self):
        data = self.data.copy()

        data.update({
            'id': self.id,
            'status': self.status,
            'createdAt': self.created_at.to_iso8601_string(extended=True),
            'links': {
                'self': url_for('main.get_application_by_id', application_id=self.id),
            }
        })

        return data

    def submit_for_approval(self):
        if self.status != 'saved':
            raise ValidationError("Only as 'saved' application can be set to 'submitted'.")
        self.create_approval_task()
        self.status = 'submitted'

    @property
    def is_existing(self):
        return self.supplier is not None

    def set_approval(self, approved):
        existing = self.is_existing

        if self.status != 'submitted':
            raise ValidationError("Only a 'submitted' application can be subject to an approval decision.")

        if approved:
            if existing:
                supplier = self.supplier
            else:
                supplier = Supplier()

            supplier.update_from_json(self.data)

            if not existing:
                self.supplier = supplier
                self.supplier.status = 'limited'

                self.status = 'approved'

            db.session.flush()

            # associate supplier with digital marketplace framework

            framework = Framework.query.filter(
                Framework.slug == 'digital-marketplace'
            ).first()
            if not SupplierFramework.query.filter(SupplierFramework.supplier_code == supplier.code,
                                                  SupplierFramework.framework_id == framework.id).first():
                sf = SupplierFramework(
                    supplier_code=supplier.code,
                    framework_id=framework.id,
                    declaration={}
                )
                db.session.add(sf)

            users = User.query.filter(User.application_id == self.id)
            for user in users:
                user.role = 'supplier'
                user.supplier_code = supplier.code

            db.session.flush()
        else:
            self.status = 'approval_rejected'

    def unreject_approval(self):
        if self.status not in ('approval_rejected'):
            raise ValidationError("Only a 'complete' or 'assessment_rejected' application can be reset to unassessed.")

        self.status = 'submitted'

    def create_approval_task(self):
        if current_app.config['JIRA_FEATURES']:
            mj = get_marketplace_jira()
            mj.create_application_approval_task(self)

    def signed_agreements(self):
        agreements = db.session.query(
            Agreement.version, Agreement.url, User.name, User.email_address, SignedAgreement.signed_at
        ).join(
            SignedAgreement, User
        ).filter(
            SignedAgreement.application_id == self.id
        ).all()

        return [a._asdict() for a in agreements]


class CaseStudy(db.Model):
    __tablename__ = 'case_study'

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(MutableDict.as_mutable(JSON), default=dict, nullable=False)
    supplier_code = db.Column(db.BigInteger, db.ForeignKey('supplier.code'), nullable=False)
    created_at = db.Column(DateTime, index=True, nullable=False, default=utcnow)

    supplier = db.relationship('Supplier', lazy='joined')

    @validates('data')
    def validates_data(self, key, data):
        data = drop_foreign_fields(data, [
            'supplierCode'
        ])
        data = strip_whitespace_from_data(data)
        data = purge_nulls_from_data(data)

        return data

    def serialize(self):
        data = self.data.copy()
        data.update({
            'id': self.id,
            'supplierCode': self.supplier_code,
            'supplierName': self.supplier.name,
            'createdAt': self.created_at.to_iso8601_string(extended=True),
            'links': {
                'self': url_for('.get_work_order', work_order_id=self.id),
                'supplier': url_for(".get_supplier", code=self.supplier_code),
            }
        })

        return data

    @staticmethod
    def from_json(data):
        def y():
            for k, v in data.items():
                c = CaseStudy()
                c.update_from_json(v)
                yield c
        return list(y())


class BriefAssessment(db.Model):
    __tablename__ = 'brief_assessment'

    brief_id = db.Column(db.Integer, db.ForeignKey('brief.id'), primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'), primary_key=True)


class Assessment(db.Model):
    __tablename__ = 'assessment'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(DateTime, index=True, nullable=False, default=utcnow)
    supplier_domain_id = db.Column(db.Integer, db.ForeignKey('supplier_domain.id'))
    supplier_domain = db.relationship(SupplierDomain, lazy='joined', innerjoin=False)

    briefs = db.relationship('Brief', secondary='brief_assessment')

    def update_from_json_before(self, data):
        if 'supplier_code' in data and 'domain_name' in data:
            self.supplier_domain = db.session.query(
                SupplierDomain
            ).join(
                Supplier, Domain
            ).filter(
                Supplier.code == data['supplier_code'],
                Domain.name == data['domain_name']
            ) .first()

            del data['supplier_code']
            del data['domain_name']

        if 'brief_id' in data:
            self.briefs = [Brief.query.filter_by(id=data['brief_id']).first()]

            del data['brief_id']

        return data


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
