import datetime

from flask import json
from nose.tools import assert_equal, assert_in
from dateutil.parser import parse as parse_time

from ..helpers import BaseApplicationTest, JSONUpdateTestMixin
from app.models import db, Framework, SupplierFramework, DraftService, User, FrameworkLot


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
                set([
                    'clarificationQuestionsOpen',
                    'framework',
                    'frameworkAgreementVersion',
                    'id',
                    'lots',
                    'name',
                    'slug',
                    'status',
                    'variations',
                    'countersignerName',
                ]))


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

            assert response.status_code == 200

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
                u'id': 1,
                u'name': u'Software as a Service',
                u'slug': u'saas',
                u'allowsBrief': False,
                u'unitSingular': u'service',
                u'oneServiceLimit': False,
                u'unitPlural': u'services',
            },
            {
                u'id': 2,
                u'name': u'Platform as a Service',
                u'slug': u'paas',
                u'allowsBrief': False,
                u'oneServiceLimit': False,
                u'unitSingular': u'service',
                u'unitPlural': u'services',
            },
            {
                u'id': 3,
                u'name': u'Infrastructure as a Service',
                u'slug': u'iaas',
                u'allowsBrief': False,
                u'oneServiceLimit': False,
                u'unitSingular': u'service',
                u'unitPlural': u'services',
            },
            {
                u'id': 4,
                u'name': u'Specialist Cloud Services',
                u'slug': u'scs',
                u'allowsBrief': False,
                u'oneServiceLimit': False,
                u'unitSingular': u'service',
                u'unitPlural': u'services',
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

        self.framework_attributes_and_values_for_update = {
            'id': 1,
            'name': "Example Framework 2",
            'slug': "example-framework-2",
            'framework': "dos",
            'frameworkAgreementDetails': {
                "countersignerName": "Dan Saxby",
                "frameworkAgreementVersion": "v1.0",
                "variations": {
                    "banana": {
                        "createdAt": "2016-06-06T20:01:34.000000Z",
                    },
                    "toblerone": {
                        "createdAt": "2016-07-06T21:09:09.000000Z",
                    },
                }
            },
            'status': "standstill",
            'clarificationQuestionsOpen': False,
            'lots': ['saas', 'paas', 'iaas', 'scs']
        }

        self.attribute_whitelist = [
            'frameworkAgreementDetails',
            'status',
            'clarificationQuestionsOpen',
        ]

    def post_framework_update(self, update):
        return self.client.post(
            '/frameworks/example-framework',
            data=json.dumps({
                'frameworks': update,
                'updated_by': 'example user'
            }),
            content_type="application/json"
        )

    def test_returns_404_on_non_existent_framework(self, open_example_framework):
        with self.app.app_context():
            response = self.client.post(
                '/frameworks/example-framework-2',
                data=json.dumps({'frameworks': {
                    'status': 'expired'
                }, 'updated_by': 'example user'}),
                content_type="application/json"
            )

            assert response.status_code == 404

    def test_can_update_whitelisted_fields(self, open_example_framework):
        valid_attributes_and_values = {
            key: value for key, value in self.framework_attributes_and_values_for_update.items()
            if key in self.attribute_whitelist
        }

        with self.app.app_context():
            for key, value in valid_attributes_and_values.items():
                response = self.post_framework_update({
                    key: value
                })

                assert response.status_code == 200
                post_data = json.loads(response.get_data())['frameworks']

                # `frameworkAgreementDetails` is not included in Framework.serialize() itself, but instead
                # each (key, value) in `frameworkAgreementDetails` is un-nested and returned with other top-level keys
                if isinstance(value, dict):
                    for nested_key, nested_value in value.items():
                        assert post_data[nested_key] == nested_value
                else:
                    assert post_data[key] == value

                get_data = json.loads(
                    self.client.get('/frameworks/example-framework').get_data()
                )['frameworks']
                assert post_data == get_data

    def test_cannot_update_non_whitelisted_fields(self, open_example_framework):
        invalid_attributes_and_values = {
            key: value for key, value in self.framework_attributes_and_values_for_update.items()
            if key not in self.attribute_whitelist
        }
        # add some random key
        invalid_attributes_and_values.update({'beverage': 'Clamato'})

        with self.app.app_context():
            for key, value in invalid_attributes_and_values.items():
                response = self.post_framework_update({
                    key: value
                })

                assert response.status_code == 400
                data = json.loads(response.get_data())['error']
                assert data == "Invalid keys for framework update: '{}'".format(key)

    def test_cannot_update_framework_with_invalid_status(self, open_example_framework):
        with self.app.app_context():
            response = self.post_framework_update({
                'status': 'invalid'
            })

            assert response.status_code == 400
            data = json.loads(response.get_data())['error']
            assert 'Invalid status value' in data

    def test_passing_in_an_empty_update_is_a_failure(self, open_example_framework):
        with self.app.app_context():
            response = self.post_framework_update({})

            assert response.status_code == 400
            data = json.loads(response.get_data())['error']
            assert data == "Framework update expects a payload"

    def test_schema_validation_for_framework_agreement_details(self, open_example_framework):
        invalid_framework_agreement_details = [
            # should be a string
            {'frameworkAgreementVersion': 1},
            # cannot be empty
            {'frameworkAgreementVersion': ""},
            # should be an object
            {'variations': 1},
            # object must have 'createdAt' key
            {'variations': {"created_at": "today"}},
            # countersigner cannot be empty
            {'countersignerName': ""},
            # invalid key
            {'frameworkAgreementDessert': "Portuguese tart"},
            # empty update
            {}
        ]

        with self.app.app_context():
            for invalid_value in invalid_framework_agreement_details:
                response = self.post_framework_update({
                    'frameworkAgreementDetails': invalid_value
                })
                assert response.status_code == 400


class TestFrameworkStats(BaseApplicationTest):
    def make_declaration(self, framework_id, supplier_ids, status=None):
        with self.app.app_context():
            db.session.query(
                SupplierFramework
            ).filter(
                SupplierFramework.framework_id == framework_id,
                SupplierFramework.supplier_id.in_(supplier_ids)
            ).update({
                SupplierFramework.declaration: {'status': status}
            }, synchronize_session=False)

            db.session.commit()

    def register_framework_interest(self, framework_id, supplier_ids):
        with self.app.app_context():
            for supplier_id in supplier_ids:
                db.session.add(
                    SupplierFramework(
                        framework_id=framework_id,
                        supplier_id=supplier_id,
                        declaration={}
                    )
                )
            db.session.commit()

    def create_drafts(self, framework_id, supplier_id_count_pairs, status='not-submitted'):
        with self.app.app_context():
            framework = Framework.query.get(framework_id)
            framework_lots = framework.lots
            for supplier_id, count in supplier_id_count_pairs:
                for ind in range(count):
                    db.session.add(
                        DraftService(
                            lot=framework_lots[ind % 4],
                            framework_id=framework_id,
                            supplier_id=supplier_id,
                            data={},
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

        self.register_framework_interest(framework.id, range(20))
        self.make_declaration(framework.id, [1, 3, 5, 7, 9, 11], status='started')
        self.make_declaration(framework.id, [0, 2, 4, 6, 8, 10], status='complete')

        self.create_drafts(framework.id, [
            (1, 1),   # 1 saas; with declaration
            (2, 7),   # 1 of each + iaas, paas, saas; with declaration
            (3, 2),   # saas + paas; with declaration
            (14, 3),  # iaas + paas + saas; without declaration
        ])
        self.create_drafts(framework.id, [
            (1, 2),   # saas + paas; with declaration
            (2, 15),  # 3 of each + iaas, paas, saas; with declaration
            (3, 2),   # saas + paas; with declaration
            (14, 7),  # 1 of each + iaas + paas + saas; without declaration
        ], status='submitted')

    def setup_data(self, framework_slug):
        self.setup_supplier_data()
        self.setup_framework_data(framework_slug)

    def test_stats(self):
        self.setup_supplier_data()
        self.setup_framework_data('g-cloud-7')
        self.setup_framework_data('digital-outcomes-and-specialists')

        response = self.client.get('/frameworks/g-cloud-7/stats')
        assert_equal(json.loads(response.get_data()), {
            u'services': [
                {u'count': 1, u'status': u'not-submitted',
                 u'declaration_made': False, u'lot': u'iaas'},
                {u'count': 2, u'status': u'not-submitted',
                 u'declaration_made': True, u'lot': u'iaas'},
                {u'count': 2, u'status': u'not-submitted',
                 u'declaration_made': False, u'lot': u'paas'},
                {u'count': 2, u'status': u'not-submitted',
                 u'declaration_made': True, u'lot': u'paas'},
                {u'count': 3, u'status': u'not-submitted',
                 u'declaration_made': False, u'lot': u'saas'},
                {u'count': 2, u'status': u'not-submitted',
                 u'declaration_made': True, u'lot': u'saas'},
                {u'count': 1, u'status': u'not-submitted',
                 u'declaration_made': True, u'lot': u'scs'},

                {u'count': 2, u'status': u'submitted',
                 u'declaration_made': False, u'lot': u'iaas'},
                {u'count': 4, u'status': u'submitted',
                 u'declaration_made': True, u'lot': u'iaas'},
                {u'count': 4, u'status': u'submitted',
                 u'declaration_made': False, u'lot': u'paas'},
                {u'count': 4, u'status': u'submitted',
                 u'declaration_made': True, u'lot': u'paas'},
                {u'count': 4, u'status': u'submitted',
                 u'declaration_made': False, u'lot': u'saas'},
                {u'count': 4, u'status': u'submitted',
                 u'declaration_made': True, u'lot': u'saas'},
                {u'count': 1, u'status': u'submitted',
                 u'declaration_made': False, u'lot': u'scs'},
                {u'count': 3, u'status': u'submitted',
                 u'declaration_made': True, u'lot': u'scs'},
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
            u'interested_suppliers': [],
            u'services': [],
            u'supplier_users': [
                {u'count': 4, u'recent_login': False},
                {u'count': 2, u'recent_login': None},
                {u'count': 5, u'recent_login': True},
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
                SupplierFramework.supplier_id.in_([0, 1])
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
            db.session.execute("UPDATE frameworks SET status='open' WHERE id=4")
            db.session.commit()
            for supplier_id in range(5):
                response = self.client.put(
                    '/suppliers/{}/frameworks/g-cloud-7'.format(supplier_id),
                    data=json.dumps({
                        'updated_by': 'example'
                    }),
                    content_type='application/json')
                assert response.status_code == 201, response.get_data(as_text=True)
            for supplier_id in range(3, 5):
                response = self.client.post(
                    '/suppliers/{}/frameworks/g-cloud-7'.format(supplier_id),
                    data=json.dumps({
                        'updated_by': 'example',
                        'frameworkInterest': {'agreementReturned': True},
                    }),
                    content_type='application/json')
                assert response.status_code == 200, response.get_data(as_text=True)

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

    def test_list_suppliers_with_agreements_returned_uses_framework_agreement_timestamp(self):
        with self.app.app_context():
            # Set supplier 3 agreement_returned_at as the highest time of suppliers 3 and 4 so we can test that
            # FrameworkAgreement.signed_agreement_returned_at takes priority over
            # SupplierFramework.agreement_returned_at when ordering by time
            db.session.execute(
                "UPDATE supplier_frameworks SET agreement_returned_at='{}' WHERE supplier_id=3".format(
                    datetime.datetime.utcnow())
            )
            db.session.commit()

            response = self.client.get('/frameworks/g-cloud-7/suppliers?agreement_returned=true')

            assert response.status_code == 200
            data = json.loads(response.get_data())
            assert len(data['supplierFrameworks']) == 2

            times = [parse_time(item['agreementReturnedAt']) for item in data['supplierFrameworks']]
            assert times[0] > times[1]

            # Check SupplierFramework.agreement_returned_at is not used (indicated by supplier 4
            # appearing before supplier 3 in our results)
            supplier_ids = [item['supplierId'] for item in data['supplierFrameworks']]
            assert supplier_ids[0] > supplier_ids[1]

    def test_list_suppliers_with_agreements_returned_includes_those_with_only_supplier_framework(self):
        with self.app.app_context():
            # Set supplier 2 to have their agreement returned information only set in the SupplierFramework table
            db.session.execute(
                "UPDATE supplier_frameworks SET agreement_returned_at='{}' WHERE supplier_id=2".format(
                    datetime.datetime.utcnow())
            )
            db.session.commit()

            response = self.client.get('/frameworks/g-cloud-7/suppliers?agreement_returned=true')

            assert response.status_code == 200
            data = json.loads(response.get_data())
            assert len(data['supplierFrameworks']) == 3

            # Check supplier 2 is included and is the top result (as their agreement returned time is the most recent)
            supplier_ids = [item['supplierId'] for item in data['supplierFrameworks']]
            assert supplier_ids[0] == 2


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
