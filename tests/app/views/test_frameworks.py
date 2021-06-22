import datetime

from flask import json
from nose.tools import assert_equal, assert_in
from dateutil.parser import parse as parse_time

from ..helpers import BaseApplicationTest, JSONUpdateTestMixin
from app.models import db, Framework, SupplierFramework, DraftService, User, FrameworkLot

import pytest


class TestListFrameworks(BaseApplicationTest):
    def test_all_frameworks_are_returned(self):
        with self.app.app_context():
            response = self.client.get('/frameworks')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
            assert_equal(len(data['frameworks']),
                         len(Framework.query.all()))
            assert_equal(
                set(data['frameworks'][0].keys()),
                {
                    'clarificationQuestionsOpen',
                    'framework',
                    'frameworkAgreementVersion',
                    'id',
                    'lots',
                    'name',
                    'slug',
                    'status',
                })


class TestCreateFramework(BaseApplicationTest):
    def framework(self, **kwargs):
        return {
            "frameworks": {
                "slug": kwargs.get("slug", "example"),
                "name": "Example",
                "framework": "g-cloud",
                "status": kwargs.get("status", "coming"),
                "clarificationQuestionsOpen": kwargs.get("clarificationQuestionsOpen", False),
                "lots": kwargs.get("lots", [
                    "saas", "paas", "iaas", "scs"
                ])
            },
            "updated_by": "example"
        }

    def teardown(self):
        super(TestCreateFramework, self).teardown()
        with self.app.app_context():
            framework = Framework.query.filter(Framework.slug == "example").first()
            if framework:
                FrameworkLot.query.filter(FrameworkLot.framework_id == framework.id).delete()
                Framework.query.filter(Framework.id == framework.id).delete()
                db.session.commit()

    def test_create_a_framework(self):
        with self.app.app_context():
            response = self.client.post("/frameworks",
                                        data=json.dumps(self.framework()),
                                        content_type="application/json")

            data = json.loads(response.get_data(as_text=True))
            assert response.status_code == 200, data

            framework = Framework.query.filter(Framework.slug == "example").first()

            assert framework.name == "Example"
            assert len(framework.lots) == 4

    def test_create_adds_audit_event(self):
        with self.app.app_context():
            self.client.post("/frameworks",
                             data=json.dumps(self.framework()),
                             content_type="application/json")

            response = self.client.get("/audit-events")

            data = json.loads(response.get_data(as_text=True))

            assert len(data["auditEvents"]) == 1
            assert data["auditEvents"][0]["type"] == "create_framework"

    def test_create_fails_if_framework_already_exists(self):
        with self.app.app_context():
            self.client.post("/frameworks",
                             data=json.dumps(self.framework()),
                             content_type="application/json")

            response = self.client.post("/frameworks",
                                        data=json.dumps(self.framework()),
                                        content_type="application/json")

            assert response.status_code == 400
            assert json.loads(response.get_data(as_text=True))["error"] == "Slug 'example' already in use"

    def test_create_fails_if_status_is_invalid(self):
        with self.app.app_context():
            response = self.client.post("/frameworks",
                                        data=json.dumps(self.framework(status="invalid")),
                                        content_type="application/json")

            assert response.status_code == 400
            assert json.loads(response.get_data(as_text=True))["error"] == "Invalid status value 'invalid'"

    def test_create_fails_if_clarification_questions_open_is_invalid(self):
        with self.app.app_context():
            response = self.client.post("/frameworks",
                                        data=json.dumps(self.framework(clarificationQuestionsOpen="invalid")),
                                        content_type="application/json")

            assert response.status_code == 400
            assert json.loads(response.get_data(as_text=True))["error"] == "Invalid framework"

    def test_create_fails_if_lot_slug_is_invalid(self):
        with self.app.app_context():
            response = self.client.post("/frameworks",
                                        data=json.dumps(self.framework(lots=["saas", "invalid", "bad"])),
                                        content_type="application/json")

            assert response.status_code == 400
            assert json.loads(response.get_data(as_text=True))["error"] == "Invalid lot slugs: bad, invalid"

    def test_create_fails_if_slug_is_invalid(self):
        with self.app.app_context():
            response = self.client.post("/frameworks",
                                        data=json.dumps(self.framework(slug="this is/invalid")),
                                        content_type="application/json")

            assert response.status_code == 400
            assert json.loads(response.get_data(as_text=True))["error"] == "Invalid slug value 'this is/invalid'"


class TestGetFramework(BaseApplicationTest):
    def test_a_single_framework_is_returned(self):
        with self.app.app_context():
            response = self.client.get('/frameworks/g-cloud-7')
            data = json.loads(response.get_data())

            assert_equal(response.status_code, 200)
            assert_equal(data['frameworks']['slug'], 'g-cloud-7')
            assert_in('status', data['frameworks'])

    def test_framework_lots_are_returned(self):
        with self.app.app_context():
            response = self.client.get('/frameworks/g-cloud-7')

        data = json.loads(response.get_data())
        assert data['frameworks']['lots'] == [
            {
                'id': 1,
                'name': 'Software as a Service',
                'slug': 'saas',
                'allowsBrief': False,
                'unitSingular': 'service',
                'oneServiceLimit': False,
                'unitPlural': 'services',
            },
            {
                'id': 2,
                'name': 'Platform as a Service',
                'slug': 'paas',
                'allowsBrief': False,
                'oneServiceLimit': False,
                'unitSingular': 'service',
                'unitPlural': 'services',
            },
            {
                'id': 3,
                'name': 'Infrastructure as a Service',
                'slug': 'iaas',
                'allowsBrief': False,
                'oneServiceLimit': False,
                'unitSingular': 'service',
                'unitPlural': 'services',
            },
            {
                'id': 4,
                'name': 'Specialist Cloud Services',
                'slug': 'scs',
                'allowsBrief': False,
                'oneServiceLimit': False,
                'unitSingular': 'service',
                'unitPlural': 'services',
            }
        ]

    def test_a_404_is_raised_if_it_does_not_exist(self):
        with self.app.app_context():
            response = self.client.get('/frameworks/biscuits-for-gov')

            assert_equal(response.status_code, 404)


class TestUpdateFramework(BaseApplicationTest, JSONUpdateTestMixin):
    endpoint = '/frameworks/example'
    method = 'post'

    def setup(self):
        super(TestUpdateFramework, self).setup()
        framework = Framework()
        # framework.id = 6,
        framework.name = 'Example G-Cloud framework'
        framework.framework = 'g-cloud'
        framework.slug = 'example'
        framework.status = 'open'

        with self.app.app_context():
            db.session.add(framework)
            db.session.commit()

    def teardown(self):
        with self.app.app_context():
            Framework.query.filter(Framework.slug == 'example').delete()
            db.session.commit()

    def test_framework_updated(self):
        with self.app.app_context():
            response = self.client.post('/frameworks/example',
                                        data=json.dumps({'frameworks': {
                                            'status': 'expired',
                                            'clarificationQuestionsOpen': False,
                                        }, 'updated_by': 'example user'}),
                                        content_type="application/json")

            assert response.status_code == 200

            framework = Framework.query.filter(Framework.slug == 'example').first()
            assert framework.status == "expired"
            assert not framework.clarification_questions_open

    def test_returns_404_on_non_existent_framework(self):
        with self.app.app_context():
            response = self.client.post('/frameworks/example2',
                                        data=json.dumps({'frameworks': {'status': 'expired'},
                                                         'updated_by': 'example user'}),
                                        content_type="application/json")

            assert response.status_code == 404

    def test_cannot_update_framework_with_invalid_status(self):
        with self.app.app_context():
            response = self.client.post('/frameworks/example',
                                        data=json.dumps({'frameworks': {'status': 'invalid'},
                                                         'updated_by': 'example user'}),
                                        content_type="application/json")

            assert response.status_code == 400

    def test_cannot_update_fields_other_than_status(self):
        with self.app.app_context():
            response = self.client.post('/frameworks/example',
                                        data=json.dumps({'frameworks': {'status': 'expired', 'name': 'Blah blah'},
                                                         'updated_by': 'example user'}),
                                        content_type="application/json")

            assert response.status_code == 400


class TestFrameworkStats(BaseApplicationTest):
    def make_declaration(self, framework_id, supplier_codes, status=None):
        with self.app.app_context():
            db.session.query(
                SupplierFramework
            ).filter(
                SupplierFramework.framework_id == framework_id,
                SupplierFramework.supplier_code.in_(supplier_codes)
            ).update({
                SupplierFramework.declaration: {'status': status}
            }, synchronize_session=False)

            db.session.commit()

    def register_framework_interest(self, framework_id, supplier_codes):
        with self.app.app_context():
            for supplier_code in supplier_codes:
                db.session.add(
                    SupplierFramework(
                        framework_id=framework_id,
                        supplier_code=supplier_code,
                        declaration={}
                    )
                )
            db.session.commit()

    def create_drafts(self, framework_id, supplier_code_count_pairs, status='not-submitted'):
        with self.app.app_context():
            framework = Framework.query.get(framework_id)
            framework_lots = framework.lots
            for supplier_code, count in supplier_code_count_pairs:
                for ind in range(count):
                    db.session.add(
                        DraftService(
                            lot=framework_lots[ind % 4],
                            framework_id=framework_id,
                            supplier_code=supplier_code,
                            data={},
                            status=status
                        )
                    )

            db.session.commit()

    def create_users(self, supplier_codes, logged_in_at):
        with self.app.app_context():
            for supplier_code in supplier_codes:
                db.session.add(
                    User(
                        name='supplier user',
                        email_address='supplier-{}@user.dmdev'.format(supplier_code),
                        password='testpassword',
                        active=True,
                        password_changed_at=datetime.datetime.utcnow(),
                        role='supplier',
                        supplier_code=supplier_code,
                        logged_in_at=logged_in_at
                    )
                )

            db.session.commit()

    def setup_supplier_data(self):
        self.setup_dummy_suppliers(30)
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

    def setup_framework_data(self, framework_slug):
        with self.app.app_context():
            framework = Framework.query.filter(Framework.slug == framework_slug).first()

        self.register_framework_interest(framework.id, list(range(20)))
        self.make_declaration(framework.id, [1, 3, 5, 7, 9, 11], status='started')
        self.make_declaration(framework.id, [0, 2, 4, 6, 8, 10], status='complete')

        self.create_drafts(framework.id, [
            (1, 1),  # 1 saas; with declaration
            (2, 7),  # 1 of each + iaas, paas, saas; with declaration
            (3, 2),  # saas + paas; with declaration
            (14, 3),  # iaas + paas + saas; without declaration
        ])
        self.create_drafts(framework.id, [
            (1, 2),  # saas + paas; with declaration
            (2, 15),  # 3 of each + iaas, paas, saas; with declaration
            (3, 2),  # saas + paas; with declaration
            (14, 7),  # 1 of each + iaas + paas + saas; without declaration
        ], status='submitted')

    def setup_data(self, framework_slug):
        self.setup_supplier_data()
        self.setup_framework_data(framework_slug)

    @pytest.mark.skip()
    def test_stats(self):
        self.setup_supplier_data()
        self.setup_framework_data('g-cloud-7')
        self.setup_framework_data('digital-outcomes-and-specialists')

        response = self.client.get('/frameworks/g-cloud-7/stats')
        assert_equal(json.loads(response.get_data()), {
            'services': [
                {'count': 1, 'status': 'not-submitted',
                 'declaration_made': False, 'lot': 'iaas'},
                {'count': 2, 'status': 'not-submitted',
                 'declaration_made': True, 'lot': 'iaas'},
                {'count': 2, 'status': 'not-submitted',
                 'declaration_made': False, 'lot': 'paas'},
                {'count': 2, 'status': 'not-submitted',
                 'declaration_made': True, 'lot': 'paas'},
                {'count': 3, 'status': 'not-submitted',
                 'declaration_made': False, 'lot': 'saas'},
                {'count': 2, 'status': 'not-submitted',
                 'declaration_made': True, 'lot': 'saas'},
                {'count': 1, 'status': 'not-submitted',
                 'declaration_made': True, 'lot': 'scs'},

                {'count': 2, 'status': 'submitted',
                 'declaration_made': False, 'lot': 'iaas'},
                {'count': 4, 'status': 'submitted',
                 'declaration_made': True, 'lot': 'iaas'},
                {'count': 4, 'status': 'submitted',
                 'declaration_made': False, 'lot': 'paas'},
                {'count': 4, 'status': 'submitted',
                 'declaration_made': True, 'lot': 'paas'},
                {'count': 4, 'status': 'submitted',
                 'declaration_made': False, 'lot': 'saas'},
                {'count': 4, 'status': 'submitted',
                 'declaration_made': True, 'lot': 'saas'},
                {'count': 1, 'status': 'submitted',
                 'declaration_made': False, 'lot': 'scs'},
                {'count': 3, 'status': 'submitted',
                 'declaration_made': True, 'lot': 'scs'},
            ],
            'interested_suppliers': [
                {'count': 7, 'declaration_status': None, 'has_completed_services': False},
                {'count': 1, 'declaration_status': None, 'has_completed_services': True},
                {'count': 5, 'declaration_status': 'complete', 'has_completed_services': False},
                {'count': 1, 'declaration_status': 'complete', 'has_completed_services': True},
                {'count': 4, 'declaration_status': 'started', 'has_completed_services': False},
                {'count': 2, 'declaration_status': 'started', 'has_completed_services': True},
            ],
            'supplier_users': [
                {'count': 4, 'recent_login': False},
                {'count': 2, 'recent_login': None},
                {'count': 5, 'recent_login': True},
            ]
        })

    def test_stats_are_for_g_cloud_7_only(self):
        self.setup_data('g-cloud-6')
        response = self.client.get('/frameworks/g-cloud-7/stats')
        assert_equal(json.loads(response.get_data()), {
            'interested_suppliers': [],
            'services': [],
            'supplier_users': [
                {'count': 4, 'recent_login': False},
                {'count': 2, 'recent_login': None},
                {'count': 5, 'recent_login': True},
            ]
        })

    def test_stats_handles_null_declarations(self):
        self.setup_data('g-cloud-7')
        with self.app.app_context():
            framework = Framework.query.filter(Framework.slug == 'g-cloud-7').first()
            db.session.query(
                SupplierFramework
            ).filter(
                SupplierFramework.framework_id == framework.id,
                SupplierFramework.supplier_code.in_([0, 1])
            ).update({
                SupplierFramework.declaration: None
            }, synchronize_session=False)

            db.session.commit()

        response = self.client.get('/frameworks/g-cloud-7/stats')

        assert response.status_code == 200


class TestGetFrameworkSuppliers(BaseApplicationTest):
    def setup(self):
        super(TestGetFrameworkSuppliers, self).setup()

        self.setup_dummy_suppliers(5)
        with self.app.app_context():
            db.session.execute("UPDATE framework SET status='open' WHERE id=4")
            db.session.commit()
            for supplier_code in range(5):
                response = self.client.put(
                    '/suppliers/{}/frameworks/g-cloud-7'.format(supplier_code),
                    data=json.dumps({
                        'updated_by': 'example'
                    }),
                    content_type='application/json')
                assert response.status_code == 201, response.get_data(as_text=True)
            for supplier_code in range(3, 5):
                response = self.client.post(
                    '/suppliers/{}/frameworks/g-cloud-7'.format(supplier_code),
                    data=json.dumps({
                        'updated_by': 'example',
                        'frameworkInterest': {'agreementReturned': True},
                    }),
                    content_type='application/json')
                assert response.status_code == 200, response.get_data(as_text=True)

    def teardown(self):
        super(TestGetFrameworkSuppliers, self).teardown()

        with self.app.app_context():
            db.session.execute("UPDATE framework SET status='open' WHERE id=4")
            db.session.commit()

    def test_list_suppliers_related_to_a_framework(self):
        with self.app.app_context():
            response = self.client.get('/frameworks/g-cloud-7/suppliers')

            assert response.status_code == 200
            data = json.loads(response.get_data())
            assert len(data['supplierFrameworks']) == 5

    def test_list_suppliers_with_agreements_returned(self):
        with self.app.app_context():
            response = self.client.get('/frameworks/g-cloud-7/suppliers?agreement_returned=true')

            assert response.status_code == 200
            data = json.loads(response.get_data())
            assert len(data['supplierFrameworks']) == 2

            times = [parse_time(item['agreementReturnedAt']) for item in data['supplierFrameworks']]
            assert times[0] > times[1]


class TestGetFrameworkInterest(BaseApplicationTest):
    def setup(self):
        super(TestGetFrameworkInterest, self).setup()

        self.register_g7_interest(5)

    def register_g7_interest(self, num):
        self.setup_dummy_suppliers(num)
        with self.app.app_context():
            for supplier_code in range(num):
                db.session.add(
                    SupplierFramework(
                        framework_id=4,
                        supplier_code=supplier_code
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
