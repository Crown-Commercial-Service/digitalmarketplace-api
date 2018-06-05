from __future__ import absolute_import

import json
import os
from datetime import datetime, timedelta

import pytest

from app import db
from app.models import Framework, User, Lot, Brief, Supplier, ContactInformation, Service, BriefClarificationQuestion
from app.models.direct_award import DirectAwardProject, DirectAwardProjectUser, DirectAwardSearch
from app.models.buyer_domains import BuyerEmailDomain

TEST_SUPPLIERS_COUNT = 3

COMPLETE_DIGITAL_SPECIALISTS_BRIEF = {
    'essentialRequirements': ['MS Paint', 'GIMP'],
    'startDate': '31-12-2016',
    'evaluationType': ['Reference', 'Interview'],
    'niceToHaveRequirements': ['LISP'],
    'existingTeam': 'Nice people.',
    'specialistWork': 'All the things',
    'workingArrangements': 'Just get the work done.',
    'organisation': 'Org.org',
    'location': 'Wales',
    'specialistRole': 'developer',
    'title': 'I need a Developer',
    'priceWeighting': 85,
    'contractLength': '3 weeks',
    'culturalWeighting': 5,
    'securityClearance': 'Developed vetting required.',
    'technicalWeighting': 10,
    'culturalFitCriteria': ['CULTURAL', 'FIT'],
    'numberOfSuppliers': 3,
    'summary': 'Doing some stuff to help out.',
    'workplaceAddress': 'Aviation House',
    'requirementsLength': '2 weeks'
}

DIRECT_AWARD_PROJECT_NAME = 'My Direct Award Project'
DIRECT_AWARD_FROZEN_TIME = '2017-01-01T00:00:00.000000Z'
DIRECT_AWARD_SEARCH_BASE = 'https://search-api.digitalmarketplace.service.gov.uk/'
DIRECT_AWARD_SEARCH_RELATIVE_URL = 'g-cloud/services/search?q=hosting'
DIRECT_AWARD_SEARCH_URL = DIRECT_AWARD_SEARCH_BASE + DIRECT_AWARD_SEARCH_RELATIVE_URL


def fixture_params(fixture_name, params):
    return pytest.mark.parametrize(fixture_name, [params], indirect=True)


class FixtureMixin(object):

    def setup_default_buyer_domain(self):
        if BuyerEmailDomain.query.filter(BuyerEmailDomain.domain_name == 'digital.gov.uk').count() == 0:
            db.session.add(BuyerEmailDomain(domain_name='digital.gov.uk'))
            db.session.commit()

    def setup_dummy_user(self, id=123, role='buyer'):
        # The user should have a valid email domain
        self.setup_default_buyer_domain()

        if role == 'admin':
            domain = 'digital.cabinet-office.gov.uk'
        elif role == 'admin-ccs-sourcing':
            domain = 'crowncommercial.gov.uk'
        else:
            domain = 'digital.gov.uk'

        if User.query.get(id):
            return id
        user = User(
            id=id,
            email_address='test+{}@{}'.format(id, domain),
            name='my name',
            password='fake password',
            active=True,
            role=role,
            password_changed_at=datetime.now()
        )
        db.session.add(user)
        db.session.commit()

        return user.id

    def setup_dummy_briefs(
        self, n, title=None, status='draft', user_id=1, data=None, brief_start=1, lot='digital-specialists',
        published_at=None, add_clarification_question=False
    ):
        user_id = self.setup_dummy_user(id=user_id)

        lot = Lot.query.filter(Lot.slug == lot).first()
        data = data or COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy()
        data['title'] = title
        for i in range(brief_start, brief_start + n):
            self.setup_dummy_brief(
                id=i,
                user_id=user_id,
                data=data,
                framework_slug='digital-outcomes-and-specialists',
                lot_slug=lot.slug,
                status=status,
                published_at=published_at,
                add_clarification_question=add_clarification_question
            )

    def setup_dummy_brief(
        self, id=None, user_id=1, status=None, data=None, published_at=None, withdrawn_at=None,
        cancelled_at=None, unsuccessful_at=None,
        framework_slug='digital-outcomes-and-specialists', lot_slug='digital-specialists',
        add_clarification_question=False
    ):
        if published_at is not None and status is not None:
            raise ValueError('Cannot provide both status and published_at')
        if withdrawn_at is not None and published_at is None:
            raise ValueError('If setting withdrawn_at then published_at must also be set')
        if not published_at:
            if status == 'closed':
                published_at = datetime.utcnow() - timedelta(days=1000)
            elif status == 'withdrawn':
                published_at = datetime.utcnow() - timedelta(days=1000)
                withdrawn_at = datetime.utcnow()
            elif status == 'cancelled':
                published_at = datetime.utcnow() - timedelta(days=1000)
                cancelled_at = datetime.utcnow()
            elif status == 'unsuccessful':
                published_at = datetime.utcnow() - timedelta(days=1000)
                unsuccessful_at = datetime.utcnow()
            else:
                published_at = None if status == 'draft' else datetime.utcnow()
        framework = Framework.query.filter(Framework.slug == framework_slug).first()
        lot = Lot.query.filter(Lot.slug == lot_slug).first()

        brief = Brief(
            id=id,
            data=data,
            framework=framework,
            lot=lot,
            users=[User.query.get(user_id)],
            published_at=published_at,
            withdrawn_at=withdrawn_at,
            cancelled_at=cancelled_at,
            unsuccessful_at=unsuccessful_at
        )

        db.session.add(brief)
        if add_clarification_question:
            db.session.add(BriefClarificationQuestion(
                brief=brief,
                question="What is the answer to the meaning of life, the Universe and everything?",
                answer="42"
            ))

        db.session.commit()
        return brief

    def setup_dummy_suppliers(self, n):
        supplier_ids = []
        for i in range(n):
            db.session.add(
                Supplier(
                    supplier_id=i,
                    name=u'Supplier {}'.format(i),
                    description='',
                    organisation_size='small',
                )
            )
            db.session.add(
                ContactInformation(
                    supplier_id=i,
                    contact_name=u'Contact for Supplier {}'.format(i),
                    email=u'{}@contact.com'.format(i),
                    postcode=u'SW1A 1AA'
                )
            )
            supplier_ids.append(i)
        db.session.commit()
        return supplier_ids

    def setup_additional_dummy_suppliers(self, n, initial):
        for i in range(1000, n + 1000):
            db.session.add(
                Supplier(
                    supplier_id=i,
                    name=u'{} suppliers Ltd {}'.format(initial, i),
                    description=''
                )
            )
            db.session.add(
                ContactInformation(
                    supplier_id=i,
                    contact_name=u'Contact for Supplier {}'.format(i),
                    email=u'{}@contact.com'.format(i),
                    postcode=u'SW1A 1AA'
                )
            )
        db.session.commit()

    def setup_dummy_service(self, service_id, supplier_id=1, data=None,
                            status='published', framework_id=1, lot_id=1, model=Service, **kwargs):
        now = datetime.utcnow()

        # lot and framework ids aren't in json responses, so we'll look for them first
        lot = Lot.query.filter(Lot.slug == kwargs.pop('lot', '')).first()
        framework = Framework.query.filter(Framework.slug == kwargs.pop('frameworkSlug', '')).first()

        service_kwargs = {
            'service_id': service_id,
            'supplier_id': kwargs.pop('supplierId', supplier_id),
            'status': kwargs.pop('status', status),
            'framework_id': framework.id if framework else framework_id,
            'lot_id': lot.id if lot else lot_id,
            'created_at': kwargs.pop('createdAt', now),
            'updated_at': kwargs.pop('updatedAt', now),
            'data': data or kwargs or {'serviceName': 'Service {}'.format(service_id)}
        }
        service = model(**service_kwargs)

        db.session.add(service)
        db.session.commit()
        return service.id

    def setup_dummy_services(self, n, supplier_id=None, framework_id=1, data=None,
                             start_id=0, lot_id=1, model=Service, status='published'):
        for i in range(start_id, start_id + n):
            self.setup_dummy_service(
                service_id=str(2000000000 + start_id + i),
                supplier_id=supplier_id or (i % TEST_SUPPLIERS_COUNT),
                framework_id=framework_id,
                lot_id=lot_id,
                model=model,
                status=status,
                data=data,
            )

    def setup_dummy_services_including_unpublished(self, n):
        self.setup_dummy_suppliers(TEST_SUPPLIERS_COUNT)
        self.setup_dummy_services(n)
        # Add extra 'enabled' and 'disabled' services
        self.setup_dummy_service(
            service_id=str(n + 2000000001),
            supplier_id=n % TEST_SUPPLIERS_COUNT,
            status='disabled')
        self.setup_dummy_service(
            service_id=str(n + 2000000002),
            supplier_id=n % TEST_SUPPLIERS_COUNT,
            status='enabled')
        # Add an extra supplier that will have no services
        db.session.add(
            Supplier(supplier_id=TEST_SUPPLIERS_COUNT, name=u'Supplier {}'
                     .format(TEST_SUPPLIERS_COUNT))
        )
        db.session.add(
            ContactInformation(
                supplier_id=TEST_SUPPLIERS_COUNT,
                contact_name=u'Contact for Supplier {}'.format(
                    TEST_SUPPLIERS_COUNT),
                email=u'{}@contact.com'.format(TEST_SUPPLIERS_COUNT),
                postcode=u'SW1A 1AA'
            )
        )
        db.session.commit()

    def setup_dos_2_framework(self, status='open', clarifications=True):
        db.session.add(
            Framework(
                id=101,
                slug=u'digital-outcomes-and-specialists-2',
                name=u'Digital Outcomes and Specialists 2',
                framework=u'digital-outcomes-and-specialists',
                status=status,
                clarification_questions_open=clarifications,
                lots=[Lot.query.filter(Lot.slug == 'digital-outcomes').first(),
                      Lot.query.filter(Lot.slug == 'digital-specialists').first(),
                      Lot.query.filter(Lot.slug == 'user-research-participants').first(),
                      Lot.query.filter(Lot.slug == 'user-research-studios').first(),
                      ],
                has_direct_award=False,
                has_further_competition=True,
            )
        )
        db.session.commit()

    def set_framework_status(self, slug, status):
        Framework.query.filter_by(slug=slug).update({'status': status})
        db.session.commit()

    def set_framework_variation(self, slug):
        Framework.query.filter_by(slug=slug).update({
            'framework_agreement_details': {
                'frameworkAgreementVersion': 'v1.0',
                'variations': {'1': {'createdAt': '2016-08-19T15:31:00.000000Z'}}
            }
        })
        db.session.commit()

    def create_direct_award_project(self, user_id, project_id=1, project_name=DIRECT_AWARD_PROJECT_NAME,
                                    created_at=DIRECT_AWARD_FROZEN_TIME):
        project = DirectAwardProject.query.get(project_id)
        if not project:
            project = DirectAwardProject(id=project_id, name=project_name, created_at=created_at)
            db.session.add(project)
            db.session.flush()

            project_user = DirectAwardProjectUser(user_id=user_id, project_id=project_id)
            db.session.add(project_user)
            db.session.commit()

        return project_id, project.external_id

    def create_direct_award_project_search(self, created_by, project_id, search_url=DIRECT_AWARD_SEARCH_URL,
                                           active=True, created_at=DIRECT_AWARD_FROZEN_TIME):
        search = DirectAwardSearch(created_by=created_by,
                                   project_id=project_id,
                                   created_at=created_at,
                                   search_url=search_url,
                                   active=active)
        db.session.add(search)
        db.session.commit()

        return search.id


def load_example_listing(name):
    file_path = os.path.join('example_listings', '{}.json'.format(name))
    with open(file_path) as f:
        return json.load(f)


def get_audit_events(client, audit_type):
    audit_response = client.get('/audit-events')
    assert audit_response.status_code == 200
    data = json.loads(audit_response.get_data(as_text=True))
    return [
        event for event in data['auditEvents'] if event['type'] == audit_type.value
    ]
