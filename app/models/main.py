# TODO split this file into per-functional-area modules

import re
from abc import ABCMeta, abstractmethod
from datetime import datetime
from uuid import uuid4

from flask import current_app
from flask_sqlalchemy import BaseQuery

import sqlalchemy.dialects.postgresql
from sqlalchemy import Sequence
from sqlalchemy import asc, desc, exists
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.event import listen
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates, backref, mapper, foreign, remote
from sqlalchemy.orm.session import Session, object_session
from sqlalchemy.sql.expression import (
    case as sql_case,
    cast as sql_cast,
    select as sql_select,
    true as sql_true,
    false as sql_false,
    null as sql_null,
    and_ as sql_and,
    or_ as sql_or,
)
from sqlalchemy.sql.sqltypes import Interval
from sqlalchemy.types import String
from sqlalchemy_utils import generic_relationship
from sqlalchemy_json import NestedMutable

from dmutils.dates import get_publishing_dates
from dmutils.formats import DATETIME_FORMAT
from dmutils.errors.api import ValidationError
from app import db, encryption
from app.utils import (
    drop_foreign_fields,
    link,
    purge_nulls_from_data,
    random_positive_external_id,
    strip_whitespace_from_data,
    url_for,
)
from app.validation import (
    is_valid_service_id, get_validation_errors, buyer_email_address_has_approved_domain,
    admin_email_address_has_approved_domain
)
from app.draft_utils import get_copiable_service_data

# there is a danger of circular imports here. as such, it is not necessarily "safe" to expect all other models to be
# present in `models` at import time, but it should be "safe" to reference any of them in this file from within a
# function or an sqlalchemy expression declared as a lambda
from app import models


class JSON(sqlalchemy.dialects.postgresql.JSON):
    """
    Override SQLAlchemy JSON class to enforce None=>SQL-NULL mapping.
    (We want to avoid JSON-null and have consistency across our models.)
    """

    def __init__(self, astext_type=None):
        super(JSON, self).__init__(none_as_null=True, astext_type=astext_type)


# Enable tracking of updates/ changes on nested attributes for all usages of the JSON class in this file
NestedMutable.associate_with(JSON)


class RemovePersonalDataModelMixin:
    """This should be added to classes we wish to remove personal data from."""

    __metaclass__ = ABCMeta

    personal_data_removed = db.Column(db.Boolean, index=False, unique=False, nullable=False, default=False)

    @abstractmethod
    def remove_personal_data(self):
        """Implement this method on the inheriting model removing personal data from the inheriting object.

        It should at some point set the 'personal_data_removed' flag to True
        """
        pass


class FrameworkLot(db.Model):
    __tablename__ = 'framework_lots'

    framework_id = db.Column(db.Integer, db.ForeignKey('frameworks.id'), primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('lots.id'), primary_key=True)


class Lot(db.Model):
    __tablename__ = 'lots'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, nullable=False, index=True)
    name = db.Column(db.String, nullable=False)
    one_service_limit = db.Column(db.Boolean, nullable=False, default=False)
    data = db.Column(JSON)

    __table_args__ = (
        # this may appear tautological (id is a unique column *on its own*, so clearly the combination of
        # id/one_service_limit is), but is required by postgres to be able to make a compound foreign key to
        # these together. fortunately it's not a big index to create.
        db.UniqueConstraint(id, one_service_limit, name="uq_lots_id_one_service_limit"),
    )

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
    UNIX_EPOCH = datetime.strptime('1970-01-01T00:00:00.000000Z', DATETIME_FORMAT)

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

    applications_close_at_utc = db.Column(db.DateTime, nullable=False, default=UNIX_EPOCH)
    intention_to_award_at_utc = db.Column(db.DateTime, nullable=False, default=UNIX_EPOCH)
    clarifications_close_at_utc = db.Column(db.DateTime, nullable=False, default=UNIX_EPOCH)
    clarifications_publish_at_utc = db.Column(db.DateTime, nullable=False, default=UNIX_EPOCH)
    framework_live_at_utc = db.Column(db.DateTime, nullable=False, default=UNIX_EPOCH)
    framework_expires_at_utc = db.Column(db.DateTime, nullable=False, default=UNIX_EPOCH)

    # We can't logically declare defaults for these values, so they must be provided explicitly at creation-time.
    # Addendum:
    # We think that storing these attributes (whether or not a thing has direct award elements and/or further
    # competition elements) at the framework level is probably the wrong level, and that technically these are
    # probably related to the lot. However, for the time being, we store it here as a proxy for the lots as our
    # frontends put a lot of faith in frameworks making the decisions for how things work.
    has_direct_award = db.Column(db.Boolean, nullable=False)
    has_further_competition = db.Column(db.Boolean, nullable=False)

    __table_args__ = (
        # We want to make sure the framework has at least one direct award or further competition component (but it can
        # have both in theory).
        db.CheckConstraint(
            sql_or(has_direct_award.is_(True), has_further_competition.is_(True)),
            name='ck_framework_has_direct_award_or_further_competition'
        ),
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
            'framework': self.framework,  # TODO: Deprecated; replaced by `family`
            'family': self.framework,
            'status': self.status,
            'clarificationQuestionsOpen': self.clarification_questions_open,
            'lots': [lot.serialize() for lot in self.lots],
            'applicationsCloseAtUTC': (
                self.applications_close_at_utc and self.applications_close_at_utc.strftime(DATETIME_FORMAT)
            ),
            'intentionToAwardAtUTC': (
                self.intention_to_award_at_utc and self.intention_to_award_at_utc.strftime(DATETIME_FORMAT)
            ),
            'clarificationsCloseAtUTC': (
                self.clarifications_close_at_utc and self.clarifications_close_at_utc.strftime(DATETIME_FORMAT)
            ),
            'clarificationsPublishAtUTC': (
                self.clarifications_publish_at_utc and self.clarifications_publish_at_utc.strftime(DATETIME_FORMAT)
            ),
            'frameworkLiveAtUTC': (
                self.framework_live_at_utc and self.framework_live_at_utc.strftime(DATETIME_FORMAT)
            ),
            'frameworkExpiresAtUTC': (
                self.framework_expires_at_utc and self.framework_expires_at_utc.strftime(DATETIME_FORMAT)
            ),
            'allowDeclarationReuse': self.allow_declaration_reuse,
            'frameworkAgreementDetails': self.framework_agreement_details or {},
            # the following are specific extracts of the above frameworkAgreementDetails which were previously used but
            # should now possibly be deprecated:
            'countersignerName': (self.framework_agreement_details or {}).get("countersignerName"),
            'frameworkAgreementVersion': (self.framework_agreement_details or {}).get("frameworkAgreementVersion"),
            'variations': (self.framework_agreement_details or {}).get("variations", {}),
            'hasDirectAward': self.has_direct_award,
            'hasFurtherCompetition': self.has_further_competition,
            'isESignatureSupported': self.framework_live_at_utc > datetime(2020, 9, 28),
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

    slug_pattern = re.compile(r"^[\w-]+$")

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


class ContactInformation(db.Model, RemovePersonalDataModelMixin):
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

    address1 = db.Column(db.String, index=False,
                         unique=False, nullable=True)

    city = db.Column(db.String, index=False,
                     unique=False, nullable=True)

    postcode = db.Column(db.String, index=False,
                         unique=False, nullable=True)

    def update_from_json(self, data):
        self.personal_data_removed = False
        self.contact_name = data.get("contactName")
        self.phone_number = data.get("phoneNumber")
        self.email = data.get("email")
        self.address1 = data.get("address1")
        self.city = data.get("city")
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
            'address1': self.address1,
            'city': self.city,
            'postcode': self.postcode,
            'personalDataRemoved': self.personal_data_removed,
            'links': links,
        }

        return filter_null_value_fields(serialized)

    def remove_personal_data(self):
        self.personal_data_removed = True

        self.contact_name = '<removed>'
        self.phone_number = '<removed>'
        self.email = '<removed>@{uuid}.com'.format(uuid=str(uuid4()))
        self.address1 = '<removed>'
        self.city = '<removed>'
        self.postcode = '<removed>'


class Supplier(db.Model):
    __tablename__ = 'suppliers'

    ORGANISATION_SIZES = (None, 'micro', 'small', 'medium', 'large')
    TRADING_STATUSES = (None,
                        "limited company (LTD)",
                        "limited liability company (LLC)",
                        "public limited company (PLC)",
                        "limited liability partnership (LLP)",
                        "sole trader",
                        "public body",
                        "other")

    # Companies House numbers consist of 8 numbers, or 2 letters followed by 6 numbers
    COMPANIES_HOUSE_NUMBER_REGEX = re.compile('^([0-9]{2}|[A-Za-z]{2})[0-9]{6}$')

    # The registration country values that come from our country picker select are in the format
    # "country" or "territory" followed by a colon and either a 2-letter country code OR three-letter/two-dash-two
    # alphanumeric territory code, for example:
    # country:GB, territory:XQZ, territory:UM-67, territory:AE-RK
    REGISTRATION_COUNTRY_REGEX = re.compile(
        '^(country:[A-Z]{2}|territory:[A-Z]{2,3}(-[A-Z0-9]{2})?)$'
    )

    # NOTE other tables tend to make foreign key references to `supplier_id` instead of this
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.BigInteger, Sequence('suppliers_supplier_id_seq'), index=True, unique=True,
                            nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String, index=False, unique=False, nullable=True)
    contact_information = db.relationship(ContactInformation,
                                          backref='supplier',
                                          lazy='joined',
                                          innerjoin=False,
                                          order_by=lambda: ContactInformation.id)
    duns_number = db.Column(db.String, unique=True, nullable=True)
    companies_house_number = db.Column(db.String, index=False, unique=False, nullable=True)
    registered_name = db.Column(db.String, index=False, unique=False, nullable=True)
    registration_country = db.Column(db.String, index=False, unique=False, nullable=True)
    other_company_registration_number = db.Column(db.String, index=False, unique=False, nullable=True)
    vat_number = db.Column(db.String, index=False, unique=False, nullable=True)
    organisation_size = db.Column(db.String, index=False, unique=False, nullable=True)
    trading_status = db.Column(db.String, index=False, unique=False, nullable=True)

    # This flag records whether a supplier has _ever_ confirmed their company details, which effectively locks down
    # certain attributes (currently company name and number, vat number, and duns number). A supplier needs to confirm
    # their details are correct for every application to a framework - this detail is stored in
    # SupplierFramework.application_company_details_confirmed
    company_details_confirmed = db.Column(db.Boolean, index=False, default=False, nullable=False)

    # This flag indicates if a supplier is no longer providing any services.
    active = db.Column(db.Boolean, default=True, server_default=sql_true(), nullable=False)

    @validates('trading_status')
    def validates_trading_status(self, key, value):
        if value not in self.TRADING_STATUSES:
            raise ValidationError("Invalid trading status '{}'".format(value))

        return value

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

    @validates('registration_country')
    def validates_registration_country(self, key, value):
        if value and not self.REGISTRATION_COUNTRY_REGEX.match(value):
            raise ValidationError("Invalid registration country '{}'".format(value))

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
            'companiesHouseNumber': self.companies_house_number,
            'contactInformation': contact_information_list,
            'links': links,
            'registeredName': self.registered_name,
            'registrationCountry': self.registration_country,
            'otherCompanyRegistrationNumber': self.other_company_registration_number,
            'vatNumber': self.vat_number,
            'organisationSize': self.organisation_size,
            'tradingStatus': self.trading_status,
            'companyDetailsConfirmed': self.company_details_confirmed,
        }

        serialized.update(data or {})

        return filter_null_value_fields(serialized)

    def update_from_json(self, data):
        self.name = data.get('name')
        self.description = data.get('description')
        self.duns_number = data.get('dunsNumber')
        self.companies_house_number = data.get('companiesHouseNumber')
        self.registered_name = data.get('registeredName')
        self.registration_country = data.get('registrationCountry')
        self.other_company_registration_number = data.get('otherCompanyRegistrationNumber')
        self.vat_number = data.get('vatNumber')
        self.organisation_size = data.get('organisationSize')
        self.trading_status = data.get('tradingStatus')

        if 'companyDetailsConfirmed' in data:
            self.company_details_confirmed = data.get('companyDetailsConfirmed')

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

    # whether to allow *this* declaration to be reused by *other* SupplierFrameworks
    # this flag allows us to disable reuse of specific declarations if e.g. they were only
    # pragmatically allowed on the framework by the framework owner.
    allow_declaration_reuse = db.Column(db.Boolean, nullable=False, default=True, server_default=sql_true())

    # Suppliers must confirm that their details are accurate for every framework application they make.
    # The flag `company_details_confirmed` is set on the Supplier object the first time a supplier confirms their
    # details (company name+number, vat number, duns number). The below SupplierFramework flag is set when a
    # supplier confirms their details with an open application to an iteration of a framework.
    application_company_details_confirmed = db.Column(db.Boolean, index=False, default=False, nullable=True)

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
    def find_by_supplier_and_framework(supplier_id, framework_slug):
        return SupplierFramework.query.filter(
            SupplierFramework.framework.has(
                Framework.slug == framework_slug
            ),
            SupplierFramework.supplier_id == supplier_id,
        )

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
            for k, v in self.agreed_variations.items()
        } if self.agreed_variations else {}

        supplier_framework = {
            "supplierId": self.supplier_id,
            "supplierName": self.supplier.name,
            "frameworkSlug": self.framework.slug,
            'frameworkFramework': self.framework.framework,  # TODO: Deprecated; replaced by frameworkFamily
            'frameworkFamily': self.framework.framework,
            "onFramework": self.on_framework,
            "agreedVariations": agreed_variations,
            "prefillDeclarationFromFrameworkSlug": (
                self.prefill_declaration_from_framework and self.prefill_declaration_from_framework.slug
            ),
            "applicationCompanyDetailsConfirmed": self.application_company_details_confirmed,
            "allowDeclarationReuse": self.allow_declaration_reuse,
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


class User(db.Model, RemovePersonalDataModelMixin):
    __tablename__ = 'users'

    ADMIN_ROLES = [
        'admin',                        # can view and suspend supplier and buyer user accounts
        'admin-ccs-category',           # can view, edit and suspend supplier services
        'admin-ccs-sourcing',           # can view framework applications and countersign agreements
        'admin-manager',                # can add, edit and disable other types of admin user
        'admin-framework-manager',      # can perform admin actions involving framework applications
        'admin-ccs-data-controller',    # can view and edit supplier company registration details
    ]

    ROLES = ADMIN_ROLES + [
        'buyer',
        'supplier',
    ]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=False, unique=False,
                     nullable=False)
    email_address = db.Column(db.String, unique=True,
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

    user_research_opted_in = db.Column(db.Boolean, index=False, unique=False, nullable=False, default=False)

    @validates('email_address')
    def validate_email_address(self, key, value):
        existing_buyer_domains = models.BuyerEmailDomain.query.all()
        if value:
            if self.role == 'buyer' and not buyer_email_address_has_approved_domain(existing_buyer_domains, value):
                raise ValidationError("invalid_buyer_domain")
            if self.role in self.ADMIN_ROLES and not admin_email_address_has_approved_domain(value):
                raise ValidationError("invalid_admin_domain")
        return value

    @validates('role')
    def validate_role(self, key, value):
        existing_buyer_domains = models.BuyerEmailDomain.query.all()
        if self.email_address:
            if value == 'buyer' and \
                    not buyer_email_address_has_approved_domain(existing_buyer_domains, self.email_address):
                raise ValidationError("invalid_buyer_domain")
            if value in self.ADMIN_ROLES and \
                    not admin_email_address_has_approved_domain(self.email_address):
                raise ValidationError("invalid_admin_domain")
        return value

    @property
    def locked(self):
        """
            Whether account has had too many failed login attempts (since counter last reset)
        """
        login_attempt_limit = current_app.config['DM_FAILED_LOGIN_LIMIT']
        return self.failed_login_count >= login_attempt_limit

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
            # When accounts are created users are logged in automatically, without creating a logged_in timestamp,
            # so we fall back to created_at if there is no logged_in timestamp.
            'loggedInAt': self.logged_in_at.strftime(DATETIME_FORMAT)
                if self.logged_in_at else self.created_at.strftime(DATETIME_FORMAT),
            'failedLoginCount': self.failed_login_count,
            'userResearchOptedIn': self.user_research_opted_in,
            'personalDataRemoved': self.personal_data_removed,
        }

        if self.role == 'supplier':
            supplier = {
                "supplierId": self.supplier.supplier_id,
                "name": self.supplier.name
            }
            if self.supplier.organisation_size:
                supplier['organisationSize'] = self.supplier.organisation_size
            user['supplier'] = supplier

        return user

    def remove_personal_data(self):
        """This method needs to remove all personal data from this object."""
        if self.role == 'buyer':
            self.email_address = '<removed><{uuid}>@{domain}'.format(
                uuid=str(uuid4()),
                domain='user.marketplace.team'
            )
        elif self.role in self.ADMIN_ROLES:
            # replace the local part but keep the domain name
            self.email_address = re.sub(r'.+?\@', '<removed><{}>@'.format(uuid4()), self.email_address)
        else:
            self.email_address = '<removed>@{uuid}.com'.format(uuid=str(uuid4()))
        self.personal_data_removed = True
        self.active = False
        self.name = '<removed>'
        self.phone_number = '<removed>'

        self.failed_login_count = 0
        self.password = encryption.hashpw(str(uuid4()))
        self.user_research_opted_in = False

    @staticmethod
    def validate_personal_data_removed(mapper, connection, instance):
        """The only time we should be able to update an object with """
        session = object_session(instance)
        if session.query(User.personal_data_removed).filter(User.id == instance.id).scalar():
            raise ValidationError("Cannot update an object once personal data has been removed")


listen(
    User,
    'before_update',
    User.validate_personal_data_removed,
    propagate=True,
)


class ServiceTableMixin(object):

    STATUSES = ('disabled', 'enabled', 'published')

    # not used as the externally-visible "pk" by actual Services in favour of service_id
    id = db.Column(db.Integer, primary_key=True)

    # used as externally-visible "pk" for Services and allows services identity to be tracked
    # across a service's lifetime. assigned randomly (see random_positive_external_id) at DraftService ->
    # Service publishing time.
    service_id = db.Column(db.String, unique=True, nullable=False)

    data = db.Column(JSON, nullable=False)
    status = db.Column(db.String, index=False, unique=False, nullable=False)

    created_at = db.Column(db.DateTime, index=False, nullable=False,
                           default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, index=False, nullable=False,
                           default=datetime.utcnow, onupdate=datetime.utcnow)

    copied_to_following_framework = db.Column(db.Boolean, nullable=False, server_default=sql_false())

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
        return (
            db.ForeignKeyConstraint(
                (cls.framework_id, cls.lot_id,),
                ("framework_lots.framework_id", "framework_lots.lot_id",),
            ),
        ) + (() if not hasattr(cls, "lot_one_service_limit") else (
            # if the model has a field named lot_one_service_limit, we enforce the one service limit where appropriate
            # on this table using a database constraint. first a constraint to ensure the lot_one_service_limit is in
            # sync with the value in the lots table
            db.ForeignKeyConstraint(
                (cls.lot_id, cls.lot_one_service_limit,),
                ("lots.id", "lots.one_service_limit",),
                name=f"fk_{cls.__tablename__}_lot_id_one_service_limit",
            ),
            # and now a conditional unique constraint where lot_one_service_limit is true
            db.Index(
                f"idx_{cls.__tablename__}_enforce_one_service_limit",
                cls.supplier_id,
                cls.lot_id,
                cls.framework_id,
                postgresql_where=cls.lot_one_service_limit,
                unique=True,
            ),
        ))

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
        return db.relationship(Lot, lazy='joined', innerjoin=True, foreign_keys=(cls.lot_id,))

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
            'frameworkSlug', 'frameworkFramework', 'frameworkFamily', 'frameworkName', 'frameworkStatus',
            'lot', 'lotSlug', 'lotName',
            'updatedAt', 'createdAt', 'links', 'copiedToFollowingFramework'
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
            'frameworkFamily': self.framework.framework,
            'frameworkName': self.framework.name,
            'frameworkStatus': self.framework.status,
            'lot': self.lot.slug,  # deprecated, use lotSlug instead
            'lotSlug': self.lot.slug,
            'lotName': self.lot.name,
            'updatedAt': self.updated_at.strftime(DATETIME_FORMAT),
            'createdAt': self.created_at.strftime(DATETIME_FORMAT),
            'status': self.status,
            'copiedToFollowingFramework': self.copied_to_following_framework,
        })

        data['links'] = link(
            "self", self.get_link()
        )

        return data

    def update_from_json(self, data):
        current_data = dict(self.data.items())
        current_data.update(data)

        # Enables us to transfer services between suppliers
        if 'supplierId' in data:
            self.supplier_id = data['supplierId']

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
            service_id=str(random_positive_external_id()),
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

    # this column will enforce its consistency with the related lot's one_service_limit, but will *not* auto-populate
    # itself. must be initialized on DraftService creation.
    lot_one_service_limit = db.Column(
        db.Boolean,
        nullable=False,
    )

    @staticmethod
    def from_service(service, questions_to_copy=None, target_framework_id=None, questions_to_exclude=None):
        draft_not_on_same_framework_as_service = target_framework_id and target_framework_id != service.framework.id

        service_data = get_copiable_service_data(
            service,
            questions_to_exclude=questions_to_exclude,
            questions_to_copy=questions_to_copy
        ) if draft_not_on_same_framework_as_service else service.data

        kwargs = {
            'framework_id': service.framework_id if not target_framework_id else target_framework_id,
            'lot': service.lot,
            'service_id': service.service_id,
            'supplier': service.supplier,
            'data': service_data,
            'status': service.status if not target_framework_id or
            target_framework_id == service.framework.id else 'not-submitted',
            'lot_one_service_limit': service.lot.one_service_limit,
        }

        if draft_not_on_same_framework_as_service:
            kwargs.pop('service_id')

        return DraftService(**kwargs)

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
            lot_one_service_limit=self.lot.one_service_limit,
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

    class query_class(BaseQuery):
        def in_lot(self, lot_slug):
            return self.filter(DraftService.lot.has(Lot.slug == lot_slug))


class AuditEvent(db.Model):
    __tablename__ = 'audit_events'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String, index=True, nullable=False)
    created_at = db.Column(db.DateTime, index=True, nullable=False, default=datetime.utcnow)
    user = db.Column(db.String)
    data = db.Column(JSONB, nullable=False)

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
            'objectType': self.object_type,
            'objectId': self.object_id,
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
    cancelled_at = db.Column(db.DateTime, index=True, nullable=True)
    unsuccessful_at = db.Column(db.DateTime, index=True, nullable=True)

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

    awarded_brief_response = db.relationship(
        'BriefResponse',
        primaryjoin="and_(Brief.id==BriefResponse.brief_id, BriefResponse.awarded_at.isnot(None))",
        uselist=False,
        lazy='joined',
        viewonly=True
    )

    outcome = db.relationship(
        "Outcome",
        primaryjoin=lambda: (sql_and(
            foreign(Brief.id) == remote(models.Outcome.brief_id),
            remote(models.Outcome.completed_at).isnot(None),
        )),
        viewonly=True,
        uselist=False,
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
            'frameworkSlug', 'frameworkFramework', 'frameworkFamily', 'frameworkName', 'frameworkStatus',
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
        one_week_addition_function = func.date_trunc('day', cls.published_at) + sql_cast('1 week 23:59:59', Interval)
        two_week_addition_function = func.date_trunc('day', cls.published_at) + sql_cast('2 weeks 23:59:59', Interval)
        return sql_case(
            [(is_one_week, one_week_addition_function)],
            else_=two_week_addition_function
        )

    @property
    def clarification_questions_closed_at(self_or_cls):
        if self_or_cls.published_at is None:
            return None
        brief_publishing_date_and_length = self_or_cls._build_date_and_length_data()

        return get_publishing_dates(brief_publishing_date_and_length)['questions_close']

    @property
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
        elif self.cancelled_at:
            return 'cancelled'
        elif self.unsuccessful_at:
            return 'unsuccessful'
        elif self.awarded_brief_response:
            return 'awarded'
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
        elif value == 'cancelled' and self.status == 'closed':
            self.cancelled_at = datetime.utcnow()
        elif value == 'unsuccessful' and self.status == 'closed':
            self.unsuccessful_at = datetime.utcnow()
        else:
            raise ValidationError("Cannot change brief status from '{}' to '{}'".format(self.status, value))

    @status.expression
    def status(cls):
        # To filter by 'awarded' status, we need an explicit EXISTS query on BriefResponse.
        # This mirrors the awarded_brief_response relationship query above.
        return sql_case([
            (cls.withdrawn_at.isnot(None), 'withdrawn'),
            (cls.published_at.is_(None), 'draft'),
            (cls.applications_closed_at > datetime.utcnow(), 'live'),
            (cls.cancelled_at.isnot(None), 'cancelled'),
            (cls.unsuccessful_at.isnot(None), 'unsuccessful'),
            (
                exists([BriefResponse.id]).where(
                    sql_and(cls.id == BriefResponse.brief_id, BriefResponse.awarded_at != None)  # noqa
                ).label('awarded_brief_response_id'), 'awarded'
            ),
        ], else_='closed')

    search_result_status_ordering = {
        "live": 0,
        "closed": 1,
        "awarded": 1,
        "cancelled": 1,
        "unsuccessful": 1,
        "draft": 2,
        "withdrawn": 2
    }

    @hybrid_property
    def status_order(self):
        return self.search_result_sort_ordering[self.status]

    @status_order.expression
    def status_order(cls):
        return sql_case([
            (cls.withdrawn_at.isnot(None), cls.search_result_status_ordering['withdrawn']),
            (cls.published_at.is_(None), cls.search_result_status_ordering['draft']),
            (cls.cancelled_at.isnot(None), cls.search_result_status_ordering['cancelled']),
            (cls.unsuccessful_at.isnot(None), cls.search_result_status_ordering['unsuccessful']),
            (
                exists([BriefResponse.id]).where(
                    sql_and(cls.id == BriefResponse.brief_id, BriefResponse.awarded_at != None)  # noqa
                ).label('awarded_brief_response_id'), cls.search_result_status_ordering['awarded']
            ),
            (cls.applications_closed_at > datetime.utcnow(), cls.search_result_status_ordering['live']),
        ], else_=cls.search_result_status_ordering['closed'])

    class query_class(BaseQuery):
        def has_statuses(self, *statuses):
            return self.filter(Brief.status.in_(statuses))

        def has_datetime_field_after(self, attr, start_datetime, inclusive=None):
            """Date filter values should be datetime objects."""
            if not isinstance(start_datetime, datetime):
                raise ValueError('Datetime object required')
            if inclusive:
                return self.filter(getattr(Brief, attr) >= str(start_datetime))
            return self.filter(getattr(Brief, attr) > str(start_datetime))

        def has_datetime_field_before(self, attr, start_datetime, inclusive=None):
            """Date filter values should be datetime objects."""
            if not isinstance(start_datetime, datetime):
                raise ValueError('Datetime object required')
            if inclusive:
                return self.filter(getattr(Brief, attr) <= str(start_datetime))
            return self.filter(getattr(Brief, attr) < str(start_datetime))

        def has_datetime_field_between(self, attr, start_datetime, end_datetime, inclusive=None):
            """
            Date filter values should be datetime objects. e.g.
                Brief.query.has_date_field_between(
                    'published_at', datetime(2017, 1, 1), datetime(2017, 1, 2, 23, 59, 59, 999999), inclusive=True
                )
            would return briefs published between 2017-01-01T00:00:00.000000Z and 2017-01-02T23:59:59.999999Z.
            """
            if not (isinstance(start_datetime, datetime) and isinstance(end_datetime, datetime)):
                raise ValueError('Datetime object required')
            if inclusive:
                return self.filter(
                    sql_and(getattr(Brief, attr) >= str(start_datetime), getattr(Brief, attr) <= str(end_datetime))
                )
            return self.filter(
                sql_and(getattr(Brief, attr) > str(start_datetime), getattr(Brief, attr) < str(end_datetime))
            )

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
            # TODO: remove top-level 'frameworkFoo' fields (use 'framework' sub-dict instead)
            'frameworkSlug': self.framework.slug,
            'frameworkFramework': self.framework.framework,
            'frameworkName': self.framework.name,
            'frameworkStatus': self.framework.status,
            'framework': {
                'family': self.framework.framework,
                'name': self.framework.name,
                'slug': self.framework.slug,
                'status': self.framework.status,
            },
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

        if self.unsuccessful_at:
            data.update({
                'unsuccessfulAt': self.unsuccessful_at.strftime(DATETIME_FORMAT)
            })

        if self.cancelled_at:
            data.update({
                'cancelledAt': self.cancelled_at.strftime(DATETIME_FORMAT)
            })

        if self.status == 'awarded':
            data.update({
                'awardedBriefResponseId': self.awarded_brief_response.id
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
    awarded_at = db.Column(db.DateTime, nullable=True)

    award_details = db.Column(JSON, nullable=True, default={})

    __table_args__ = (
        # this may appear tautological (id is a unique column *on its own*, so clearly the combination of id/brief_id
        # is), but is required by postgres to be able to make a compound foreign key to these together
        db.UniqueConstraint(id, brief_id, name="uq_brief_responses_id_brief_id"),
    )

    brief = db.relationship('Brief', lazy='joined', backref=backref("brief_responses", lazy="select"))
    supplier = db.relationship('Supplier', lazy='joined')

    @validates('data')
    def validates_data(self, key, data):
        data = drop_foreign_fields(data, [
            'supplierId', 'briefId',
        ])
        data = strip_whitespace_from_data(data)
        data = purge_nulls_from_data(data)

        return data

    @validates('awarded_at')
    def validates_awarded_at(self, key, awarded_at):
        if self.awarded_at is not None:
            raise ValidationError('Cannot remove or change award datestamp on previously awarded Brief Response')
        if not awarded_at:
            return None
        if self.brief.status != "closed":
            raise ValidationError('Brief response can not be awarded if the brief is not closed')
        if self.status != 'pending-awarded':
            raise ValidationError('Brief response can not be awarded if response has not been submitted')
        return awarded_at

    def update_from_json(self, data):
        current_data = dict(self.data.items())
        current_data.update(data)

        self.data = current_data

    @hybrid_property
    def status(self):
        if self.awarded_at:
            return 'awarded'
        elif self.award_details:
            return 'pending-awarded'
        if self.submitted_at:
            return 'submitted'
        else:
            return 'draft'

    @status.expression
    def status(cls):
        return sql_case([
            (cls.awarded_at.isnot(None), 'awarded'),
            (cls.award_details.cast(String) != '{}', 'pending-awarded'),
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

    def serialize(self, with_data: bool = True):
        """
            :param with_data: allows serialization to be produced while omitting the majority of the content
            that comes from the `data` field. This tends to constitute the bulk of the volume of the serialized
            result, so this is useful in cases where response size is becoming an issue. the
            `essentialRequirementsMet` key (present in DOS2 BRs onwards)is pragmatically included anyway because it
            is referenced in some important listing views.
        """
        data = {k: v for k, v in self.data.items() if with_data or k == "essentialRequirementsMet"}
        parent_brief = self.brief.serialize()
        parent_brief_fields = ['id', 'title', 'status', 'applicationsClosedAt', 'framework']
        data.update({
            'id': self.id,
            'brief': {
                **{key: parent_brief[key] for key in parent_brief_fields if key in parent_brief},
            },
            'briefId': self.brief_id,
            'supplierId': self.supplier_id,
            'supplierName': self.supplier.name,
            'supplierOrganisationSize': self.supplier.organisation_size,
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

        if self.status == "awarded":
            data.update({
                'awardDetails': self.award_details,
                'awardedAt': self.awarded_at.strftime(DATETIME_FORMAT)
            })
        elif self.status == 'pending-awarded':
            data.update({
                'awardDetails': {'pending': True}
            })

        return purge_nulls_from_data(data)


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
        return value.strip() if isinstance(value, str) else value

    @validates('answer')
    def validates_answer(self, key, value):
        return value.strip() if isinstance(value, str) else value

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

# Index for searching audit events by the supplier id included in the data blob. Both `supplierId` and `supplier_id`
#  have been used, hence the need for the coalesce. Audits all now use `supplierId` consistantly.
db.Index(
    'idx_audit_events_data_supplier_id',
    func.coalesce(AuditEvent.data['supplierId'].astext, AuditEvent.data['supplier_id'].astext),
    postgresql_where=func.coalesce(
        AuditEvent.data['supplierId'].astext,
        AuditEvent.data['supplier_id'].astext,
    ) != sql_null()
)

# Index for searching audit events by the draft id included in the data blob.
db.Index(
    'idx_audit_events_data_draft_id',
    AuditEvent.data['draftId'].astext,
    postgresql_where=AuditEvent.data['draftId'].astext != sql_null()
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

db.Index(
    'idx_brief_responses_unique_awarded_at_per_brief_id',
    BriefResponse.brief_id,
    postgresql_where=BriefResponse.awarded_at != sql_null(),
    unique=True
)


def filter_null_value_fields(obj):
    return dict(
        filter(lambda x: x[1] is not None, obj.items())
    )
