import datetime

from flask import json
from nose.tools import assert_equal

from dmutils.audit import AuditTypes

from ..helpers import BaseApplicationTest
from app.models import db, Framework, SupplierFramework, DraftService, AuditEvent, Supplier, User


class TestListFrameworks(BaseApplicationTest):
    def test_all_frameworks_are_returned(self):
        with self.app.app_context():
            response = self.client.get('/frameworks')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
            assert_equal(len(data['frameworks']),
                         len(Framework.query.all()))
            assert_equal(sorted(data['frameworks'][0].keys()),
                         ['framework', 'id', 'name', 'slug', 'status'])


class TestGetFramework(BaseApplicationTest):
    def test_a_single_framework_is_returned(self):
        with self.app.app_context():
            response = self.client.get('/frameworks/g-cloud-7')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
            assert_equal(data['frameworks']['slug'], 'g-cloud-7')

    def test_a_404_is_raised_if_it_does_not_exist(self):
        with self.app.app_context():
            response = self.client.get('/frameworks/biscuits-for-gov')

            assert_equal(response.status_code, 404)


class TestGetFrameworkStatus(BaseApplicationTest):
    def test_status_is_returned_for_existing_frameworks(self):
        with self.app.app_context():
            response = self.client.get('/frameworks/g-cloud-6/status')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
            assert_equal(data['status'], "live")

            response = self.client.get('/frameworks/g-cloud-4/status')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
            assert_equal(data['status'], "expired")

    def test_404_for_non_existing_frameworks(self):
        with self.app.app_context():
            response = self.client.get('/frameworks/biscuits-for-gov/status')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 404)


class TestFrameworkStats(BaseApplicationTest):
    def create_selection_answers(self, framework_id, supplier_ids, status=None):
        with self.app.app_context():
            for supplier_id in supplier_ids:
                db.session.add(
                    SupplierFramework(
                        framework_id=framework_id,
                        supplier_id=supplier_id,
                        declaration={'status': status},
                    )
                )

            db.session.commit()

    def create_framework_interest_audit_event(self, framework_id, supplier_ids):
        with self.app.app_context():
            for supplier_id in supplier_ids:
                db.session.add(
                    AuditEvent(
                        audit_type=AuditTypes.register_framework_interest,
                        user='supplier@user.dmdev',
                        data='{}',
                        db_object=Supplier.query.filter(
                            Supplier.supplier_id == supplier_id
                        ).first()
                    )
                )

            db.session.commit()

    def create_drafts(self, framework_id, supplier_id_count_pairs, status='not-submitted'):
        with self.app.app_context():
            for supplier_id, count in supplier_id_count_pairs:
                for ind in range(count):
                    db.session.add(
                        DraftService(
                            framework_id=framework_id,
                            supplier_id=supplier_id,
                            data={
                                'lot': ['IaaS', 'PaaS', 'SaaS', 'SCS'][ind % 4]
                            },
                            status=status
                        )
                    )

            db.session.commit()

    def create_users(self, supplier_ids, logged_in_at):
        with self.app.app_context():
            for supplier_id in supplier_ids:
                db.session.add(
                    User(
                        name='supplier user',
                        email_address='supplier-{}@user.dmdev'.format(supplier_id),
                        password='testpassword',
                        active=True,
                        password_changed_at=datetime.datetime.utcnow(),
                        role='supplier',
                        supplier_id=supplier_id,
                        logged_in_at=logged_in_at
                    )
                )

            db.session.commit()

    def setup_data(self, framework_slug):
        with self.app.app_context():
            framework = Framework.query.filter(Framework.slug == framework_slug).first()

        self.setup_dummy_suppliers(30)
        self.create_framework_interest_audit_event(framework.id, range(20))
        self.create_selection_answers(framework.id, [1, 3, 5, 7, 9, 11], status='started')
        self.create_selection_answers(framework.id, [0, 2, 4, 6, 8, 10], status='complete')
        self.create_drafts(framework.id, [
            (1, 1),   # 1 IaaS; with declaration
            (2, 7),   # 1 of each + IaaS, PaaS, SaaS; with declaration
            (3, 2),   # IaaS + PaaS; with declaration
            (14, 3),  # IaaS + PaaS + SaaS; without declaration
        ])
        self.create_drafts(framework.id, [
            (1, 2),   # IaaS + PaaS; with declaration
            (2, 15),  # 3 of each + IaaS, PaaS, SaaS; with declaration
            (3, 2),   # IaaS + PaaS; with declaration
            (14, 7),  # 1 of each + IaaS + PaaS + SaaS; without declaration
        ], status='submitted')

        self.create_users(
            [1, 2, 3, 4, 5],
            logged_in_at=datetime.datetime.utcnow() - datetime.timedelta(days=1)
        )

        self.create_users(
            [6, 7, 8, 9],
            logged_in_at=datetime.datetime.utcnow() - datetime.timedelta(days=10)
        )

        self.create_users(
            [10, 11],
            logged_in_at=None
        )

    def test_stats(self):
        self.setup_data('g-cloud-7')

        response = self.client.get('/frameworks/g-cloud-7/stats')
        assert_equal(json.loads(response.get_data()), {
            u'services': [
                {u'count': 3, u'status': u'not-submitted',
                 u'declaration_made': False, u'lot': u'IaaS'},
                {u'count': 2, u'status': u'not-submitted',
                 u'declaration_made': True, u'lot': u'IaaS'},
                {u'count': 4, u'status': u'submitted',
                 u'declaration_made': False, u'lot': u'IaaS'},
                {u'count': 4, u'status': u'submitted',
                 u'declaration_made': True, u'lot': u'IaaS'},

                {u'count': 2, u'status': u'not-submitted',
                 u'declaration_made': False, u'lot': u'PaaS'},
                {u'count': 2, u'status': u'not-submitted',
                 u'declaration_made': True, u'lot': u'PaaS'},
                {u'count': 4, u'status': u'submitted',
                 u'declaration_made': False, u'lot': u'PaaS'},
                {u'count': 4, u'status': u'submitted',
                 u'declaration_made': True, u'lot': u'PaaS'},

                {u'count': 1, u'status': u'not-submitted',
                 u'declaration_made': True, u'lot': u'SCS'},
                {u'count': 1, u'status': u'submitted',
                 u'declaration_made': False, u'lot': u'SCS'},
                {u'count': 3, u'status': u'submitted',
                 u'declaration_made': True, u'lot': u'SCS'},

                {u'count': 1, u'status': u'not-submitted',
                 u'declaration_made': False, u'lot': u'SaaS'},
                {u'count': 2, u'status': u'not-submitted',
                 u'declaration_made': True, u'lot': u'SaaS'},
                {u'count': 2, u'status': u'submitted',
                 u'declaration_made': False, u'lot': u'SaaS'},
                {u'count': 4, u'status': u'submitted',
                 u'declaration_made': True, u'lot': u'SaaS'}
            ],
            u'interested_suppliers': [
                {u'count': 7, u'declaration_status': None, u'has_completed_services': False},
                {u'count': 1, u'declaration_status': None, u'has_completed_services': True},
                {u'count': 5, u'declaration_status': 'complete', u'has_completed_services': False},
                {u'count': 1, u'declaration_status': 'complete', u'has_completed_services': True},
                {u'count': 4, u'declaration_status': 'started', u'has_completed_services': False},
                {u'count': 2, u'declaration_status': 'started', u'has_completed_services': True},
            ],
            u'supplier_users': [
                {u'count': 4, u'recent_login': False},
                {u'count': 2, u'recent_login': None},
                {u'count': 5, u'recent_login': True},
            ]
        })

    def test_stats_are_for_g_cloud_7_only(self):
        self.setup_data('g-cloud-6')
        response = self.client.get('/frameworks/g-cloud-7/stats')
        assert_equal(json.loads(response.get_data()), {
            u'interested_suppliers': [
                # No suppliers with completed G7 services
                {u'count': 8, u'declaration_status': None, u'has_completed_services': False},
                {u'count': 6, u'declaration_status': 'complete', u'has_completed_services': False},
                {u'count': 6, u'declaration_status': 'started', u'has_completed_services': False},
            ],
            u'services': [],
            u'supplier_users': [
                {u'count': 4, u'recent_login': False},
                {u'count': 2, u'recent_login': None},
                {u'count': 5, u'recent_login': True},
            ]
        })


class TestGetFrameworkInterest(BaseApplicationTest):
    def setup(self):
        super(TestGetFrameworkInterest, self).setup()

        self.register_g7_interest(5)

    def register_g7_interest(self, num):
        self.setup_dummy_suppliers(num)
        with self.app.app_context():
            for supplier_id in range(num):
                db.session.add(
                    SupplierFramework(
                        framework_id=4,
                        supplier_id=supplier_id
                    )
                )
            db.session.commit()

    def test_interested_suppliers_are_returned(self):
        with self.app.app_context():
            response = self.client.get('/frameworks/g-cloud-7/interest')

            assert_equal(response.status_code, 200)
            data = json.loads(response.get_data())
            assert_equal(data['interestedSuppliers'], [0, 1, 2, 3, 4])

    def test_a_404_is_raised_if_it_does_not_exist(self):
        with self.app.app_context():
            response = self.client.get('/frameworks/biscuits-for-gov/interest')

            assert_equal(response.status_code, 404)
