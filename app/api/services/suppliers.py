from datetime import datetime, timedelta

import pytz
from sqlalchemy import and_, func, literal, or_, select, union
from sqlalchemy.orm import joinedload, noload, raiseload
from sqlalchemy.dialects.postgresql import aggregate_order_by

from app import db
from app.api.helpers import Service
from app.models import (CaseStudy,
                        Domain,
                        Framework,
                        Supplier,
                        SupplierDomain,
                        SupplierFramework,
                        User)


class SuppliersService(Service):
    __model__ = Supplier

    def __init__(self, *args, **kwargs):
        super(SuppliersService, self).__init__(*args, **kwargs)

    def get_suppliers_by_contact_email(self, emails):
        return (db.session.query(Supplier)
                .filter(func.lower(Supplier.data['contact_email'].astext).in_(emails))
                .filter(Supplier.status != 'deleted')
                .all())

    def get_supplier_by_code(self, code):
        return (
            db
            .session
            .query(
                Supplier
            )
            .options(
                joinedload(Supplier.domains)
                .joinedload(SupplierDomain.domain)
            )
            .filter(Supplier.code == code)
            .one_or_none()
        )

    def get_suppliers_by_name_keyword(self, keyword, framework_slug=None, category=None):
        query = (db.session.query(Supplier)
                 .filter(Supplier.name.ilike('%{}%'.format(keyword.encode('utf-8'))))
                 .filter(Supplier.status != 'deleted')
                 .options(
                     joinedload(Supplier.frameworks),
                     joinedload(Supplier.domains),
                     joinedload(Supplier.prices),
                     joinedload('domains.domain'),
                     joinedload('prices.service_role'),
                     joinedload('frameworks.framework'),
                     noload('frameworks.framework.lots'),
                     raiseload('*')))
        if framework_slug:
            query = query.outerjoin(SupplierFramework).outerjoin(Framework)
            query = query.filter(Framework.slug == framework_slug)
        if category:
            query = query.outerjoin(SupplierDomain)
            query = query.filter(SupplierDomain.domain_id == category).filter(SupplierDomain.status == 'assessed')
        query.order_by(Supplier.name.asc()).limit(20)
        return query.all()

    def get_supplier_assessed_status(self, supplier_id, category):
        return (
            db
            .session
            .query(SupplierDomain.status)
            .filter(SupplierDomain.domain_id == category)
            .filter(SupplierDomain.supplier_id == supplier_id)
            .order_by(SupplierDomain.id.desc())
            .limit(1)
            .scalar()
        )

    def get_supplier_max_price_for_domain(self, supplier_code, domain_name):
        return (
            db
            .session
            .query(Supplier.data['pricing'][domain_name]['maxPrice'].astext.label('maxPrice'))
            .filter(
                Supplier.code == supplier_code,
                Supplier.data['pricing'][domain_name]['maxPrice'].isnot(None)
            )
            .scalar()
        )

    def get_metrics(self):
        supplier_count = (
            db
            .session
            .query(
                func.count(Supplier.id)
            )
            .outerjoin(SupplierFramework)
            .outerjoin(Framework)
            .filter(
                Supplier.abn != Supplier.DUMMY_ABN,
                Supplier.status != 'deleted',
                or_(Framework.slug == 'digital-marketplace', ~Supplier.frameworks.any())
            )
            .scalar()
        )

        return {
            "supplier_count": supplier_count
        }

    def get_supplier_contacts_union(self):
        authorised_representative = select([
            Supplier.code,
            Supplier.data['email'].astext.label('email_address')
        ])
        business_contact = select([
            Supplier.code,
            Supplier.data['contact_email'].astext.label('email_address')
        ])
        user_email_addresses = (select([
            User.supplier_code.label('code'),
            User.email_address
        ]).where(User.active))

        return union(authorised_representative, business_contact, user_email_addresses).alias('email_addresses')

    def get_supplier_contacts(self, supplier_code):
        email_addresses = self.get_supplier_contacts_union()

        result = (
            db
            .session
            .query(
                email_addresses.c.email_address
            )
            .filter(
                email_addresses.c.code == supplier_code
            )
            .all()
        )

        return [r._asdict() for r in result]

    def get_suppliers_codes_with_domains(self, rejected_price_only):
        subquery = None
        if rejected_price_only:
            subquery = (
                db.session.query(SupplierDomain.supplier_id)
                .filter(SupplierDomain.price_status == 'rejected')
                .subquery()
            )
        else:
            subquery = db.session.query(SupplierDomain.supplier_id).subquery()

        result = (
            db
            .session
            .query(
                Supplier.code
            )
            .filter(
                Supplier.status != 'deleted',
                Supplier.data['recruiter'].astext.in_(['no', 'both']),
                Supplier.id.in_(subquery)
            )
            .all()
        )

        return [r._asdict() for r in result]

    def get_suppliers_with_expiring_documents(self, days):
        today = datetime.now(pytz.timezone('Australia/Sydney'))

        # Find out which of the supplier's documents have expired or are expiring soon
        liability = (select([Supplier.code, Supplier.name, literal('liability').label('type'),
                             Supplier.data['documents']['liability']['expiry'].astext.label('expiry')])
                     .where(and_(Supplier.data['documents']['liability']['expiry'].isnot(None),
                                 func.to_date(Supplier.data['documents']['liability']['expiry'].astext, 'YYYY-MM-DD') ==
                                 (today.date() + timedelta(days=days)))))
        workers = (select([Supplier.code, Supplier.name, literal('workers').label('type'),
                           Supplier.data['documents']['workers']['expiry'].astext.label('expiry')])
                   .where(and_(Supplier.data['documents']['workers']['expiry'].isnot(None),
                               func.to_date(Supplier.data['documents']['workers']['expiry'].astext, 'YYYY-MM-DD') ==
                               (today.date() + timedelta(days=days)))))

        expiry_dates = union(liability, workers).alias('expiry_dates')

        # Aggregate the document details so they can be returned with the results
        documents = (db.session.query(expiry_dates.columns.code, expiry_dates.columns.name,
                                      func.json_agg(
                                          func.json_build_object(
                                              'type', expiry_dates.columns.type,
                                              'expiry', expiry_dates.columns.expiry)).label('documents'))
                     .group_by(expiry_dates.columns.code, expiry_dates.columns.name)
                     .subquery('expired_documents'))

        # Find email addresses associated with the supplier
        email_addresses = self.get_supplier_contacts_union()

        # Aggregate the email addresses so they can be returned with the results
        aggregated_emails = (db.session.query(email_addresses.columns.code,
                                              func.json_agg(
                                                  email_addresses.columns.email_address
                                              ).label('email_addresses'))
                             .group_by(email_addresses.columns.code)
                             .subquery())

        # Combine the list of email addresses and documents
        results = (db.session.query(documents.columns.code, documents.columns.name, documents.columns.documents,
                                    aggregated_emails.columns.email_addresses)
                   .join(aggregated_emails,
                         documents.columns.code == aggregated_emails.columns.code)
                   .order_by(documents.columns.code)
                   .all())

        return [r._asdict() for r in results]

    def get_suppliers_with_unassessed_domains_and_all_case_studies_rejected(self):
        case_study_query = (
            db.session.query(
                CaseStudy.supplier_code.label('supplier_code'),
                CaseStudy.data['service'].astext.label('domain'),
                func.count(CaseStudy.id).label('count')
            )
            .group_by(CaseStudy.supplier_code, CaseStudy.data['service'].astext)
        )

        subquery = (
            case_study_query
            .intersect(
                case_study_query
                .filter(CaseStudy.status == 'rejected')
            )
            .subquery()
        )

        results = (
            db
            .session
            .query(
                Supplier.id,
                Supplier.code,
                Supplier.name,
                func.json_agg(aggregate_order_by(Domain.name, Domain.name)).label('domains')
            )
            .join(SupplierDomain, Domain)
            .join(subquery, and_(
                Supplier.code == subquery.columns.supplier_code,
                Domain.name == subquery.columns.domain
            ))
            .filter(
                Supplier.status != 'deleted',
                Supplier.data['recruiter'].astext.in_(['no', 'both']),
                SupplierDomain.status == 'unassessed'
            )
            .group_by(Supplier.id, Supplier.code, Supplier.name)
            .all()
        )

        return [r._asdict() for r in results]

    def save_supplier(self, supplier, do_commit=True):
        return self.save(supplier, do_commit)
