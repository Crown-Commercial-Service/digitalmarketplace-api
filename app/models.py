import random
from datetime import datetime
import re

from flask import current_app
from flask_sqlalchemy import BaseQuery
from six import string_types, iteritems

from sqlalchemy import asc, desc
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import INTERVAL
import sqlalchemy.dialects.postgresql
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates, backref, mapper
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import (
    case as sql_case,
    cast as sql_cast,
    select as sql_select,
    false as sql_false,
    and_ as sql_and,
)
from sqlalchemy.types import String
from sqlalchemy import Sequence
from sqlalchemy_utils import generic_relationship

from dmutils.formats import DATETIME_FORMAT, DATE_FORMAT
from dmutils.dates import get_publishing_dates

from . import db
from .utils import link, url_for, strip_whitespace_from_data, drop_foreign_fields, purge_nulls_from_data
from .validation import is_valid_service_id, is_valid_buyer_email, get_validation_errors


class JSON(sqlalchemy.dialects.postgresql.JSON):
    """
    Override SQLAlchemy JSON class to enforce None=>SQL-NULL mapping.
    (We want to avoid JSON-null and have consistency across our models.)
    """

    def __init__(self, astext_type=None):
        super(JSON, self).__init__(none_as_null=True, astext_type=astext_type)


class FrameworkLot(db.Model):
    __tablename__ = 'framework_lots'

    framework_id = db.Column(db.Integer, db.ForeignKey('frameworks.id'), primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('lots.id'), primary_key=True)


class ValidationError(ValueError):
    def __init__(self, message):
        self.message = message


class Lot(db.Model):
    __tablename__ = 'lots'

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
    __tablename__ = 'frameworks'

    STATUSES = (
        'coming', 'open', 'pending', 'standstill', 'live', 'expired'
    )
    FRAMEWORKS = (
        'g-cloud',
        'digital-outcomes-and-specialists',
    )

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, nullable=False, unique=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    framework = db.Column(db.String(), index=True, nullable=False)
    framework_agreement_details = db.Column(JSON, nullable=True)
    status = db.Column(
        db.String(),
        index=True, nullable=False,
        default='pending'
    )
    clarification_questions_open = db.Column(db.Boolean, nullable=False, default=False)
    lots = db.relationship(
        'Lot',
        secondary="framework_lots",
        lazy='joined',
        innerjoin=False,
        order_by=Lot.id,
        backref='frameworks'
    )
    allow_declaration_reuse = db.Column(db.Boolean, nullable=False, default=False)
    application_close_date = db.Column(db.DateTime, nullable=True)

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
            'status': self.status,
            'clarificationQuestionsOpen': self.clarification_questions_open,
            'lots': [lot.serialize() for lot in self.lots],
            'applicationCloseDate': (
                self.application_close_date and self.application_close_date.strftime(DATETIME_FORMAT)
            ),
            'allowDeclarationReuse': self.allow_declaration_reuse,
            'frameworkAgreementDetails': self.framework_agreement_details or {},
            # the following are specific extracts of the above frameworkAgreementDetails which were previously used but
            # should now possibly be deprecated:
            'countersignerName': (self.framework_agreement_details or {}).get("countersignerName"),
            'frameworkAgreementVersion': (self.framework_agreement_details or {}).get("frameworkAgreementVersion"),
            'variations': (self.framework_agreement_details or {}).get("variations", {}),
        }

    def get_supplier_ids_for_completed_service(self):
        """Only suppliers whose service has a status of submitted or failed."""
        results = db.session.query(
            DraftService
        ).filter(
            DraftService.status.in_(('submitted', 'failed')),
            DraftService.framework_id == self.id
        ).with_entities(
            DraftService.supplier_id
        ).distinct()
        # Unpack list of lists and set
        return set(item for sublist in results for item in sublist)

    @validates('status')
    def validates_status(self, key, value):
        if value not in self.STATUSES:
            raise ValidationError("Invalid status value '{}'".format(value))

        return value

    @validates('framework')
    def validates_framework(self, key, framework):
        return Framework.validate_framework(framework)

    @staticmethod
    def validate_framework(framework):
        if framework not in Framework.FRAMEWORKS:
            raise ValidationError("Invalid framework value '{}'".format(framework))
        return framework

    slug_pattern = re.compile("^[\w-]+$")

    @validates('slug')
    def validates_slug(self, key, slug):
        if not self.slug_pattern.match(slug):
            raise ValidationError("Invalid slug value '{}'".format(slug))
        return slug

    @validates('clarification_questions_open')
    def validates_clarification_questions_open(self, key, value):
        # Note that because of an undefined order of setting attributes on this model
        # (ie, between this `clarification_questions_open` and `status`)
        # it _is_ possible to be in a state where `clarification_questions_open` is `True`
        # and the new status is not one of the allowed ones
        # if `self.status` *at the time of the update* is one of the allowed ones
        if (
            self.status is not None and
            self.status not in ('coming', 'open', 'pending')
            and value is True
        ):
            raise ValidationError("Clarification questions are only permitted while the framework is open")
        return value

    def __repr__(self):
        return '<{}: {} slug={}>'.format(self.__class__.__name__, self.name, self.slug)


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
                         unique=False, nullable=True)

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

    @staticmethod
    def from_json(data):
        c = ContactInformation()
        c.update_from_json(data)
        return c

    def get_link(self):
        return url_for("main.update_contact_information",
                       supplier_id=self.supplier_id,
                       contact_id=self.id)

    def serialize(self):
        links = link(
            "self", self.get_link()
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

    ORGANISATION_SIZES = (None, 'micro', 'small', 'medium', 'large')

    # Companies House numbers consist of 8 numbers, or 2 letters followed by 6 numbers
    COMPANIES_HOUSE_NUMBER_REGEX = re.compile('^([0-9]{2}|[A-Za-z]{2})[0-9]{6}$')

    # NOTE other tables tend to make foreign key references to `supplier_id` instead of this
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.BigInteger, Sequence('suppliers_supplier_id_seq'), index=True, unique=True,
                            nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String, index=False, unique=False, nullable=True)
    contact_information = db.relationship(ContactInformation,
                                          backref='supplier',
                                          lazy='joined',
                                          innerjoin=False)
    duns_number = db.Column(db.String, index=True, unique=True, nullable=True)
    esourcing_id = db.Column(db.String, index=False, unique=False, nullable=True)
    companies_house_number = db.Column(db.String, index=False, unique=False, nullable=True)
    clients = db.Column(JSON, default=list, nullable=False)
    registered_name = db.Column(db.String, index=False, unique=False, nullable=True)
    registration_country = db.Column(db.String, index=False, unique=False, nullable=True)
    other_company_registration_number = db.Column(db.String, index=False, unique=False, nullable=True)
    registration_date = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    vat_number = db.Column(db.String, index=False, unique=False, nullable=True)
    organisation_size = db.Column(db.String, index=False, unique=False, nullable=True)
    trading_status = db.Column(db.String, index=False, unique=False, nullable=True)

    @validates('organisation_size')
    def validates_org_size(self, key, value):
        if value not in self.ORGANISATION_SIZES:
            raise ValidationError("Invalid organisation size '{}'".format(value))

        return value

    @validates('companies_house_number')
    def validates_companies_house_number(self, key, value):
        if value and not self.COMPANIES_HOUSE_NUMBER_REGEX.match(value):
            raise ValidationError("Invalid companies house number '{}'".format(value))

        return value

    # Drop this method once the supplier front end is using SupplierFramework counts
    def get_service_counts(self):
        services = db.session.query(
            Framework.name, func.count(Framework.name)
        ).join(Service.framework).filter(
            Framework.status == 'live',
            Service.status == 'published',
            Service.supplier_id == self.supplier_id
        ).group_by(Framework.name).all()

        return dict(services)

    def get_link(self):
        return url_for("main.get_supplier", supplier_id=self.supplier_id)

    def serialize(self, data=None):
        links = link(
            "self", self.get_link()
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
            'companiesHouseNumber': self.companies_house_number,
            'contactInformation': contact_information_list,
            'links': links,
            'clients': self.clients,
            'registeredName': self.registered_name,
            'registrationCountry': self.registration_country,
            'otherCompanyRegistrationNumber': self.other_company_registration_number,
            'registrationDate': self.registration_date.strftime(DATE_FORMAT) if self.registration_date else None,
            'vatNumber': self.vat_number,
            'organisationSize': self.organisation_size,
            'tradingStatus': self.trading_status,
        }

        serialized.update(data or {})

        return filter_null_value_fields(serialized)

    def update_from_json(self, data):
        self.name = data.get('name')
        self.description = data.get('description')
        self.duns_number = data.get('dunsNumber')
        self.esourcing_id = data.get('eSourcingId')
        self.clients = data.get('clients')
        self.companies_house_number = data.get('companiesHouseNumber')
        self.registered_name = data.get('registeredName')
        self.registration_country = data.get('registrationCountry')
        self.other_company_registration_number = data.get('otherCompanyRegistrationNumber')
        self.vat_number = data.get('vatNumber')
        self.organisation_size = data.get('organisationSize')
        self.trading_status = data.get('tradingStatus')

        if 'registrationDate' in data:
            self.registration_date = datetime.strptime(data.get('registrationDate'), DATE_FORMAT)

        return self


class SupplierFramework(db.Model):
    __tablename__ = 'supplier_frameworks'

    supplier_id = db.Column(db.Integer,
                            db.ForeignKey('suppliers.supplier_id'),
                            primary_key=True)
    framework_id = db.Column(db.Integer,
                             db.ForeignKey('frameworks.id'),
                             primary_key=True)
    declaration = db.Column(JSON)
    on_framework = db.Column(db.Boolean, nullable=True)
    agreed_variations = db.Column(JSON)

    prefill_declaration_from_framework_id = db.Column(
        db.Integer,
        db.ForeignKey('frameworks.id'),
        nullable=True,
    )

    __table_args__ = (
        db.ForeignKeyConstraint(
            [supplier_id, prefill_declaration_from_framework_id],
            # looks weird, but remember this is a self-relationship
            [supplier_id, framework_id],
        ),
        {}
    )

    supplier = db.relationship(Supplier, lazy='joined', innerjoin=True)
    framework = db.relationship(Framework, lazy='joined', innerjoin=True, foreign_keys=(framework_id,))

    prefill_declaration_from_framework = db.relationship(
        Framework,
        lazy='joined',
        innerjoin=False,
        foreign_keys=[prefill_declaration_from_framework_id]
    )

    prefill_declaration_from_supplier_framework = db.relationship(
        "SupplierFramework",
        lazy="select",
        foreign_keys=(supplier_id, prefill_declaration_from_framework_id,),
        remote_side=(supplier_id, framework_id,),
        # we probably don't want people inadvertantly flipping the supplier_id through writing to this relationship
        viewonly=True,
    )

    # vvvv current_framework_agreement defined further down (after FrameworkAgreement) vvvv

    @hybrid_property
    def supplier_organisation_size(self):
        return self.declaration.get('organisationSize') if self.declaration else None

    @supplier_organisation_size.expression
    def supplier_organisation_size(cls):
        return cls.declaration['organisationSize'].astext

    @validates('declaration')
    def validates_declaration(self, key, value):
        value = strip_whitespace_from_data(value)
        value = purge_nulls_from_data(value)

        return value

    @validates('agreed_variations')
    def validates_agreed_variations(self, key, value):
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
    def find_by_supplier_and_framework(supplier_id, framework_slug):
        return SupplierFramework.find_by_framework(framework_slug).filter(
            SupplierFramework.supplier_id == supplier_id
        ).first()

    @staticmethod
    def get_service_counts(supplier_id):

        count_services_query = db.session.query(
            Service.framework_id, Service.status, func.count()
        ).filter(
            Service.supplier_id == supplier_id
        ).group_by(
            Service.framework_id,
            Service.status
        ).all()

        count_drafts_query = db.session.query(
            DraftService.framework_id, DraftService.status, func.count()
        ).filter(
            DraftService.supplier_id == supplier_id
        ).group_by(
            DraftService.framework_id,
            DraftService.status
        ).all()

        return {
            (row[0], row[1]): row[2]
            for row in count_services_query + count_drafts_query
        }

    @staticmethod
    def serialize_agreed_variation(agreed_variation, with_users=False):
        if not (with_users and agreed_variation.get("agreedUserId")):
            return agreed_variation

        user = User.query.filter(
            User.id == agreed_variation["agreedUserId"]
        ).first()
        if not user:
            return agreed_variation

        return dict(agreed_variation, **{
            "agreedUserName": user.name,
            "agreedUserEmail": user.email_address,
        })

    def serialize(self, data=None, with_users=False, with_declaration=True):
        agreed_variations = {
            k: self.serialize_agreed_variation(v, with_users=with_users)
            for k, v in iteritems(self.agreed_variations or {})
        }

        supplier_framework = {
            "supplierId": self.supplier_id,
            "supplierName": self.supplier.name,
            "frameworkSlug": self.framework.slug,
            'frameworkFramework': self.framework.framework,
            "onFramework": self.on_framework,
            "agreedVariations": agreed_variations,
            "prefillDeclarationFromFrameworkSlug": (
                self.prefill_declaration_from_framework and self.prefill_declaration_from_framework.slug
            ),
        }
        if with_declaration:
            supplier_framework.update({
                "declaration": self.declaration,
            })
        if data:
            supplier_framework.update(data)

        agreement = self.current_framework_agreement
        if agreement:
            supplier_framework.update({
                'agreementId': agreement.id,
                'agreementReturned': bool(agreement.signed_agreement_returned_at),
                'agreementReturnedAt': (
                    agreement.signed_agreement_returned_at and
                    agreement.signed_agreement_returned_at.strftime(DATETIME_FORMAT)
                ),
                'agreementDetails': agreement.signed_agreement_details,
                'agreementPath': agreement.signed_agreement_path,
                'countersigned': bool(agreement.countersigned_agreement_returned_at),
                'countersignedAt': (
                    agreement.countersigned_agreement_returned_at and
                    agreement.countersigned_agreement_returned_at.strftime(DATETIME_FORMAT)
                ),
                'countersignedDetails': agreement.countersigned_agreement_details,
                'countersignedPath': agreement.countersigned_agreement_path,
                'agreementStatus': agreement.status
            })
        else:
            supplier_framework.update({
                "agreementId": None,
                "agreementReturned": False,
                "agreementReturnedAt": None,
                "agreementDetails": None,
                "agreementPath": None,
                "countersigned": False,
                "countersignedAt": None,
                "countersignedDetails": None,
                "countersignedPath": None,
                "agreementStatus": None
            })

        if with_users:
            if (supplier_framework.get("agreementDetails") or {}).get("uploaderUserId"):
                user = User.query.filter(
                    User.id == supplier_framework['agreementDetails']['uploaderUserId']
                ).first()

                if user:
                    supplier_framework['agreementDetails']['uploaderUserName'] = user.name
                    supplier_framework['agreementDetails']['uploaderUserEmail'] = user.email_address

            if (supplier_framework.get("countersignedDetails") or {}).get("approvedByUserId"):
                user = User.query.filter(
                    User.id == supplier_framework['countersignedDetails']['approvedByUserId']
                ).first()

                if user:
                    supplier_framework['countersignedDetails']['approvedByUserName'] = user.name
                    supplier_framework['countersignedDetails']['approvedByUserEmail'] = user.email_address

        return supplier_framework


class FrameworkAgreement(db.Model):
    __tablename__ = 'framework_agreements'

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, nullable=False)
    framework_id = db.Column(db.Integer, nullable=False)
    signed_agreement_details = db.Column(JSON)
    signed_agreement_path = db.Column(db.String)
    signed_agreement_returned_at = db.Column(db.DateTime)
    signed_agreement_put_on_hold_at = db.Column(db.DateTime)
    countersigned_agreement_details = db.Column(JSON)
    countersigned_agreement_path = db.Column(db.String)
    countersigned_agreement_returned_at = db.Column(db.DateTime)

    __table_args__ = (
        db.ForeignKeyConstraint(
            [supplier_id, framework_id],
            [SupplierFramework.supplier_id, SupplierFramework.framework_id]
        ),
        {}
    )

    supplier_framework = db.relationship(
        SupplierFramework,
        lazy="joined",
        backref=backref('framework_agreements', lazy="joined"),
    )

    def update_signed_agreement_details_from_json(self, data):
        if self.signed_agreement_details:
            current_data = self.signed_agreement_details.copy()
        else:
            current_data = {}

        current_data.update(data)

        self.signed_agreement_details = current_data

    @validates('signed_agreement_details')
    def validates_signed_agreement_details(self, key, data):
        if data is None:
            return data

        data = strip_whitespace_from_data(data)
        data = purge_nulls_from_data(data)

        return data

    @hybrid_property
    def most_recent_signature_time(self):
        # Time of most recent signing or countersignature
        return self.countersigned_agreement_returned_at or self.signed_agreement_returned_at

    @most_recent_signature_time.expression
    def most_recent_signature_time(cls):
        # Time of most recent signing or countersignature
        return func.coalesce(cls.countersigned_agreement_returned_at, cls.signed_agreement_returned_at)

    @hybrid_property
    def status(self):
        if self.countersigned_agreement_path:
            return 'countersigned'
        elif self.countersigned_agreement_returned_at:
            return 'approved'
        elif self.signed_agreement_put_on_hold_at:
            return 'on-hold'
        elif self.signed_agreement_returned_at:
            return 'signed'
        else:
            return 'draft'

    @status.expression
    def status(cls):
        return sql_case([
            (cls.countersigned_agreement_path.isnot(None), 'countersigned'),
            (cls.countersigned_agreement_returned_at.isnot(None), 'approved'),
            (cls.signed_agreement_put_on_hold_at.isnot(None), 'on-hold'),
            (cls.signed_agreement_returned_at.isnot(None), 'signed')
        ], else_='draft')

    def serialize(self):
        return purge_nulls_from_data({
            'id': self.id,
            'supplierId': self.supplier_id,
            'frameworkSlug': self.supplier_framework.framework.slug,
            'status': self.status,
            'signedAgreementDetails': self.signed_agreement_details,
            'signedAgreementPath': self.signed_agreement_path,
            'signedAgreementReturnedAt': (
                self.signed_agreement_returned_at and
                self.signed_agreement_returned_at.strftime(DATETIME_FORMAT)
            ),
            'signedAgreementPutOnHoldAt': (
                self.signed_agreement_put_on_hold_at and
                self.signed_agreement_put_on_hold_at.strftime(DATETIME_FORMAT)
            ),
            'countersignedAgreementDetails': self.countersigned_agreement_details,
            'countersignedAgreementReturnedAt': (
                self.countersigned_agreement_returned_at and
                self.countersigned_agreement_returned_at.strftime(DATETIME_FORMAT)
            ),
            'countersignedAgreementPath': self.countersigned_agreement_path
        })


# a non_primary mapper representing the "current" framework agreement of each SupplierFramework
SupplierFramework._CurrentFrameworkAgreement = mapper(
    FrameworkAgreement,
    sql_select([FrameworkAgreement]).where(
        FrameworkAgreement.status != "draft",
    ).order_by(
        FrameworkAgreement.supplier_id,
        FrameworkAgreement.framework_id,
        desc(FrameworkAgreement.most_recent_signature_time),
    ).distinct(
        FrameworkAgreement.supplier_id,
        FrameworkAgreement.framework_id,
    ).alias(),
    non_primary=True,
)
SupplierFramework.current_framework_agreement = db.relationship(
    SupplierFramework._CurrentFrameworkAgreement,
    lazy="joined",
    uselist=False,
    viewonly=True,
)


class User(db.Model):
    __tablename__ = 'users'

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

    supplier_id = db.Column(db.BigInteger,
                            db.ForeignKey('suppliers.supplier_id'),
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
        return url_for('main.get_user_by_id', user_id=self.id)

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
                "supplierId": self.supplier.supplier_id,
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

    data = db.Column(JSON, nullable=False)
    status = db.Column(db.String, index=False, unique=False, nullable=False)

    created_at = db.Column(db.DateTime, index=False, nullable=False,
                           default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, index=False, nullable=False,
                           default=datetime.utcnow, onupdate=datetime.utcnow)

    @declared_attr
    def supplier_id(cls):
        return db.Column(db.BigInteger, db.ForeignKey('suppliers.supplier_id'),
                         index=True, unique=False, nullable=False)

    @declared_attr
    def framework_id(cls):
        return db.Column(db.BigInteger, db.ForeignKey('frameworks.id'),
                         index=True, unique=False, nullable=False)

    @declared_attr
    def __table_args__(cls):
        return (db.ForeignKeyConstraint([cls.framework_id, cls.lot_id],
                                        ['framework_lots.framework_id', 'framework_lots.lot_id']),
                {})

    @declared_attr
    def lot_id(cls):
        return db.Column(db.BigInteger, db.ForeignKey('lots.id'),
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
            'supplierId', 'supplierName',
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
            'supplierId': self.supplier.supplier_id,
            'supplierName': self.supplier.name,
            'frameworkSlug': self.framework.slug,
            'frameworkFramework': self.framework.framework,
            'frameworkName': self.framework.name,
            'frameworkStatus': self.framework.status,
            'lot': self.lot.slug,  # deprecated, use lotSlug instead
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
        return '<{}: service_id={}, supplier_id={}, lot={}>'.format(
            self.__class__.__name__,
            self.service_id, self.supplier_id, self.lot
        )


class Service(db.Model, ServiceTableMixin):
    __tablename__ = 'services'

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
        return url_for("main.get_service", service_id=self.service_id)


class ArchivedService(db.Model, ServiceTableMixin):
    """
        A record of a Service's past state
    """
    __tablename__ = 'archived_services'

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
        return url_for("main.get_archived_service",
                       archived_service_id=service_id)

    def get_link(self):
        return self.link_object(self.id)

    def update_from_json(self, data):
        raise NotImplementedError('Archived services should not be changed')


class DraftService(db.Model, ServiceTableMixin):
    __tablename__ = 'draft_services'

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

        data['links']['publish'] = url_for('main.publish_draft_service', draft_id=self.id)
        data['links']['complete'] = url_for('main.complete_draft_service', draft_id=self.id)
        data['links']['copy'] = url_for('main.copy_draft_service', draft_id=self.id)

        return data

    def get_link(self):
        return url_for("main.fetch_draft_service", draft_id=self.id)


class AuditEvent(db.Model):
    __tablename__ = 'audit_events'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String, index=True, nullable=False)
    created_at = db.Column(db.DateTime, index=True, nullable=False, default=datetime.utcnow)
    user = db.Column(db.String)
    data = db.Column(JSON, nullable=False)

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
                "self": url_for("main.list_audits"),
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
    __tablename__ = 'briefs'

    CLARIFICATION_QUESTIONS_OPEN_DAYS = 7
    CLARIFICATION_QUESTIONS_PUBLISHED_DAYS = 1
    APPLICATIONS_OPEN_DAYS = 14

    id = db.Column(db.Integer, primary_key=True)

    framework_id = db.Column(db.Integer, db.ForeignKey('frameworks.id'), nullable=False)
    _lot_id = db.Column("lot_id", db.Integer, db.ForeignKey('lots.id'), nullable=False)
    is_a_copy = db.Column(db.Boolean, nullable=False, server_default=sql_false())

    data = db.Column(JSON, nullable=False)
    created_at = db.Column(db.DateTime, index=True, nullable=False,
                           default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, index=True, nullable=False,
                           default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime, index=True, nullable=True)
    withdrawn_at = db.Column(db.DateTime, index=True, nullable=True)

    __table_args__ = (db.ForeignKeyConstraint([framework_id, _lot_id],
                                              ['framework_lots.framework_id', 'framework_lots.lot_id']),
                      {})

    users = db.relationship('User', secondary='brief_users')
    framework = db.relationship('Framework', lazy='joined')
    lot = db.relationship('Lot', lazy='joined')
    clarification_questions = db.relationship(
        "BriefClarificationQuestion",
        order_by="BriefClarificationQuestion.published_at",
        lazy='select',
    )

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
        """
        Set the applications_closed_at based on whether a brief has 'requirementsLength' one week or two weeks.
        """
        is_one_week = cls.data['requirementsLength'].astext == '1 week'
        one_week_addition_function = func.date_trunc('day', cls.published_at) + sql_cast('1 week 23:59:59', INTERVAL)
        two_week_addition_function = func.date_trunc('day', cls.published_at) + sql_cast('2 weeks 23:59:59', INTERVAL)
        return sql_case(
            [(is_one_week, one_week_addition_function)],
            else_=two_week_addition_function
        )

    @hybrid_property
    def clarification_questions_closed_at(self_or_cls):
        if self_or_cls.published_at is None:
            return None
        brief_publishing_date_and_length = self_or_cls._build_date_and_length_data()

        return get_publishing_dates(brief_publishing_date_and_length)['questions_close']

    @hybrid_property
    def clarification_questions_published_by(self_or_cls):
        if self_or_cls.published_at is None:
            return None
        brief_publishing_date_and_length = self_or_cls._build_date_and_length_data()

        return get_publishing_dates(brief_publishing_date_and_length)['answers_close']

    @hybrid_property
    def clarification_questions_are_closed(self_or_cls):
        return datetime.utcnow() > self_or_cls.clarification_questions_closed_at

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
        data = self.data.copy()
        title = data.get('title', '')
        if 0 < len(title) <= 95:
            data['title'] = u"{} copy".format(title)

        do_not_copy = ["startDate", "questionAndAnswerSessionDetails", "researchDates"]
        data = {key: value for key, value in data.items() if key not in do_not_copy}

        framework = Framework.query.filter(
            Framework.framework == self.framework.framework,
            Framework.status == 'live'
        ).one()

        return Brief(
            data=data,
            is_a_copy=True,
            framework=framework,
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

    def serialize(self, with_users=False, with_clarification_questions=False):
        data = dict(self.data.items())

        data.update({
            'id': self.id,
            'status': self.status,
            'frameworkSlug': self.framework.slug,
            'frameworkFramework': self.framework.framework,
            'frameworkName': self.framework.name,
            'frameworkStatus': self.framework.status,
            'isACopy': self.is_a_copy,
            'lot': self.lot.slug,  # deprecated, use lotSlug instead
            'lotSlug': self.lot.slug,
            'lotName': self.lot.name,
            'createdAt': self.created_at.strftime(DATETIME_FORMAT),
            'updatedAt': self.updated_at.strftime(DATETIME_FORMAT),
        })

        if with_clarification_questions:
            data['clarificationQuestions'] = [
                question.serialize() for question in self.clarification_questions
            ]

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
            'self': url_for('main.get_brief', brief_id=self.id),
            'framework': url_for('main.get_framework', framework_slug=self.framework.slug),
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
    __tablename__ = 'brief_users'

    brief_id = db.Column(db.Integer, db.ForeignKey('briefs.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)


class BriefResponse(db.Model):
    __tablename__ = 'brief_responses'

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(JSON, nullable=False)

    brief_id = db.Column(db.Integer, db.ForeignKey('briefs.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=False)

    created_at = db.Column(db.DateTime, index=True, nullable=False, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime, nullable=True)

    brief = db.relationship('Brief', lazy='joined')
    supplier = db.relationship('Supplier', lazy='joined')

    @validates('data')
    def validates_data(self, key, data):
        data = drop_foreign_fields(data, [
            'supplierId', 'briefId',
        ])
        data = strip_whitespace_from_data(data)
        data = purge_nulls_from_data(data)

        return data

    def update_from_json(self, data):
        current_data = dict(self.data.items())
        current_data.update(data)

        self.data = current_data

    @hybrid_property
    def status(self):
        if self.submitted_at:
            return 'submitted'
        else:
            return 'draft'

    @status.expression
    def status(cls):
        return sql_case([
            (cls.submitted_at.isnot(None), 'submitted'),
        ], else_='draft')

    def validate(self, enforce_required=True, required_fields=None, max_day_rate=None):
        errs = get_validation_errors(
            'brief-responses-{}-{}'.format(
                self.brief.framework.slug,
                self.brief.lot.slug),
            self.data,
            enforce_required=enforce_required,
            required_fields=required_fields
        )

        if (
            (required_fields and 'essentialRequirements' in required_fields or enforce_required) and
            'essentialRequirements' not in errs and
            len(self.data.get('essentialRequirements', [])) != len(self.brief.data['essentialRequirements'])
        ):
            errs['essentialRequirements'] = 'answer_required'

        if (
            (required_fields and 'niceToHaveRequirements' in required_fields or enforce_required) and
            'niceToHaveRequirements' not in errs and
            len(self.data.get('niceToHaveRequirements', [])) != len(self.brief.data.get('niceToHaveRequirements', []))
        ):
            errs['niceToHaveRequirements'] = 'answer_required'

        if (
            (required_fields and 'dayRate' in required_fields or enforce_required) and
            max_day_rate and 'dayRate' not in errs
        ):
            if float(self.data['dayRate']) > float(max_day_rate):
                errs['dayRate'] = 'max_less_than_min'

        if errs:
            raise ValidationError(errs)

    def serialize(self):
        data = self.data.copy()
        parent_brief = self.brief.serialize()
        parent_brief_fields = ['id', 'title', 'status', 'applicationsClosedAt', 'frameworkSlug']
        data.update({
            'id': self.id,
            'brief': {key: parent_brief[key] for key in parent_brief_fields if key in parent_brief},
            'briefId': self.brief_id,
            'supplierId': self.supplier_id,
            'supplierName': self.supplier.name,
            'supplierOrganisationSize': self.supplier_framework.supplier_organisation_size,
            'createdAt': self.created_at.strftime(DATETIME_FORMAT),
            'submittedAt': (
                self.submitted_at and self.submitted_at.strftime(DATETIME_FORMAT)
            ),
            'status': self.status,
            'links': {
                'self': url_for('main.get_brief_response', brief_response_id=self.id),
                'brief': url_for('main.get_brief', brief_id=self.brief_id),
                'supplier': url_for("main.get_supplier", supplier_id=self.supplier_id),
            }
        })

        return purge_nulls_from_data(data)


# The following is the code to fetch the supplier_framework of a BriefResponse.
# A standard relationship would not work in this case because we want to join 3 tables, BriefResponses, Briefs and
# SupplierFrameworks but use a key from BriefResponses (supplier_id) to denote the record from SupplierFrameworks.
# See docs below, specifically; 'the A->secondary->B pattern does not support any references between A and B directly'.
# http://docs.sqlalchemy.org/en/latest/orm/join_conditions.html#relationship-to-non-primary-mapper

# Create a join of 3 tables (like a TEMP TABLE) that, in SQL, would look like:
# SELECT *
# FROM brief_responses
#   JOIN briefs
#     ON brief_responses.brief_id = briefs.id
#   JOIN supplier_frameworks AS sf
#     ON sf.supplier_id = brief_responses.supplier_id AND sf.framework_id = briefs.framework_id
# ;
brief_responses_supplier_frameworks_join = brsf = db.join(
    BriefResponse,
    Brief,
    BriefResponse.brief_id == Brief.id
).join(
    SupplierFramework,
    sql_and(
        SupplierFramework.framework_id == Brief.framework_id,
        SupplierFramework.supplier_id == BriefResponse.supplier_id
    )
)

# Map the join to SupplierFramework to tell the ORM what object we want to get from the join.
# We also have to disambiguate the duplicate name fields (id, data, created_at etc.) using the properties kwarg.
brief_responses_supplier_frameworks_to_supplier_frameworks_mapping = mapper(
    SupplierFramework,
    brief_responses_supplier_frameworks_join,
    properties={
        "brief_id": [brsf.c.briefs_id, brsf.c.brief_responses_brief_id],
        'briefs_data': brsf.c.briefs_data,
        'briefs_created_at': brsf.c.briefs_created_at,
        'supplier_id': [brsf.c.brief_responses_supplier_id, brsf.c.supplier_frameworks_supplier_id],
        'framework_id': [brsf.c.supplier_frameworks_framework_id, brsf.c.briefs_framework_id],
    },
    non_primary=True,
)

# Join the mapping to the brief_responses table as a relationship:
# SELECT supplier_framework.* FROM brief_responses JOIN brsf ON brief_responses.id = brsf.brief_responses_id
BriefResponse.supplier_framework = db.relationship(
    brief_responses_supplier_frameworks_to_supplier_frameworks_mapping,
    primaryjoin=db.foreign(BriefResponse.id) == brief_responses_supplier_frameworks_join.c.brief_responses_id,
    lazy="joined",
    uselist=False,
    viewonly=True,
)


class BriefClarificationQuestion(db.Model):
    __tablename__ = 'brief_clarification_questions'

    id = db.Column(db.Integer, primary_key=True)
    _brief_id = db.Column("brief_id", db.Integer, db.ForeignKey("briefs.id"), nullable=False)

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


class DirectAwardProject(db.Model):
    __tablename__ = 'direct_award_projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    locked_at = db.Column(db.DateTime, nullable=True)  # When the project's active search/es are final and cannot change
    active = db.Column(db.Boolean, default=True, nullable=False)

    users = db.relationship(User, secondary='direct_award_project_users', order_by=lambda: DirectAwardProjectUser.id)

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.strftime(DATETIME_FORMAT),
            "locked_at": self.locked_at.strftime(DATETIME_FORMAT) if self.locked_at is not None else None,
            "active": self.active
        }

    @validates('name')
    def _assert_active_project(self, key, value):
        if self.locked_at:
            raise ValidationError('Cannot change project name after locking it ({})'.format(self.id))

        return value


class DirectAwardProjectUser(db.Model):
    __tablename__ = 'direct_award_project_users'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('direct_award_projects.id'), index=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True, nullable=False)


class DirectAwardSearch(db.Model):
    __tablename__ = 'direct_award_searches'

    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('direct_award_projects.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # When this search was first saved.
    searched_at = db.Column(db.DateTime, nullable=True)  # When this search was run for the project services download.
    search_url = db.Column(db.Text, nullable=False)  # Search API URL to hit when retrieving services.
    active = db.Column(db.Boolean, default=True, nullable=False, index=True)  # Is the 'current' search for the project

    # Access archived_services relating to this search. Should only have related services after the project
    # has been downloaded, and this is the search for that project that was chosen as the search to longlist/shortlist
    # against.
    # Note: an archived service is not a service from an old framework, as one might think. An ArchivedService is
    # created when an attribute on a service is changed. By storing the ArchivedService id we are referencing a service
    # in a given state at a specific time. We can still access the live version of the service through the Archived
    # Service, but by storing this we have the flexibility to show either the live state or the state at the time
    # the user ran the search.
    archived_services = db.relationship(ArchivedService, secondary='direct_award_search_result_entries',
                                        order_by=lambda: DirectAwardSearchResultEntry.id)

    project = db.relationship(DirectAwardProject)
    user = db.relationship(User)

    # Partial index on project_id,active==1. Enforces only one active search per project at a time.
    __table_args__ = (db.Index('idx_project_id_active', project_id, active, unique=True,
                               postgresql_where=db.Column('active')),)

    def serialize(self):
        return {
            "id": self.id,
            "created_by": self.created_by,
            "project_id": self.project_id,
            "created_at": self.created_at.strftime(DATETIME_FORMAT),
            "searched_at": self.searched_at.strftime(DATETIME_FORMAT) if self.searched_at is not None else None,
            "search_url": self.search_url,
            "active": self.active
        }

    @validates('id', 'created_by', 'project_id', 'created_at', 'searched_at', 'search_url', 'active')
    def _assert_active_project(self, key, value):
        if self.project and self.project.locked_at:
            raise ValidationError('Cannot change attributes of a search under a project ({}) that '
                                  'has been locked.'.format(self.project_id))

        return value


class DirectAwardSearchResultEntry(db.Model):
    __tablename__ = 'direct_award_search_result_entries'

    id = db.Column(db.Integer, primary_key=True)
    search_id = db.Column(db.Integer, db.ForeignKey('direct_award_searches.id'), index=True, nullable=False)
    archived_service_id = db.Column(db.Integer, db.ForeignKey('archived_services.id'), index=True, nullable=False)


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


# DEPRECATED - remove in a migration once service update admin app feature has been updated
db.Index(
    'idx_audit_events_type_acknowledged',
    AuditEvent.type,
    AuditEvent.acknowledged,
)

# partial index for supplier_update-monitoring admin views. specifically this
# ordering should allow the index to be used for earliest_for_each_object's
# ordering-followed-by-DISTINCT ON
db.Index(
    'idx_audit_events_created_at_per_obj_partial',
    AuditEvent.object_type,
    AuditEvent.object_id,
    AuditEvent.created_at,
    AuditEvent.id,
    postgresql_where=sql_and(AuditEvent.acknowledged == sql_false(), AuditEvent.type == "update_service"),
)


def filter_null_value_fields(obj):
    return dict(
        filter(lambda x: x[1] is not None, obj.items())
    )


def generate_new_service_id(framework_slug):
    # FIXME framework_slug parameter ignored??
    return str(random.randint(10 ** 14, 10 ** 15 - 1))
