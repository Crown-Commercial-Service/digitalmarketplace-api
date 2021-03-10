import datetime
import mock
import pytest

from itertools import cycle

from flask import json
from freezegun import freeze_time
from sqlalchemy.exc import IntegrityError

from tests.bases import BaseApplicationTest, JSONUpdateTestMixin
from app.models import db, Framework, SupplierFramework, DraftService, User, FrameworkLot, AuditEvent, Brief
from tests.helpers import FixtureMixin
from app.main.views.frameworks import FRAMEWORK_UPDATE_WHITELISTED_ATTRIBUTES_MAP


class TestListFrameworks(BaseApplicationTest):
    def test_all_frameworks_are_returned(self):
        response = self.client.get('/frameworks')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert len(data['frameworks']) == len(Framework.query.all())
        assert set(data['frameworks'][0].keys()) == set([
            'allowDeclarationReuse',
            'applicationsCloseAtUTC',
            'clarificationQuestionsOpen',
            'clarificationsCloseAtUTC',
            'clarificationsPublishAtUTC',
            'countersignerName',
            'framework',
            'family',
            'frameworkAgreementDetails',
            'frameworkAgreementVersion',
            'frameworkExpiresAtUTC',
            'frameworkLiveAtUTC',
            'id',
            'intentionToAwardAtUTC',
            'lots',
            'name',
            'slug',
            'status',
            'variations',
            'hasDirectAward',
            'hasFurtherCompetition',
            'isESignatureSupported',
        ])


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
                ]),
                "hasDirectAward": True,
                "hasFurtherCompetition": False,
            },
            "updated_by": "example"
        }

    def teardown(self):
        framework = Framework.query.filter(Framework.slug == "example").first()
        if framework:
            FrameworkLot.query.filter(FrameworkLot.framework_id == framework.id).delete()
            Framework.query.filter(Framework.id == framework.id).delete()
            db.session.commit()
        super(TestCreateFramework, self).teardown()

    def test_create_a_framework(self):
        response = self.client.post("/frameworks",
                                    data=json.dumps(self.framework()),
                                    content_type="application/json")

        assert response.status_code == 201

        framework = Framework.query.filter(Framework.slug == "example").first()

        assert framework.name == "Example"
        assert len(framework.lots) == 4

    def test_create_adds_audit_event(self):
        framework_response = self.client.post(
            "/frameworks",
            data=json.dumps(self.framework()),
            content_type="application/json",
        )
        audit_response = self.client.get("/audit-events")

        framework_id = json.loads(framework_response.data)['frameworks']['id']
        data = json.loads(audit_response.get_data(as_text=True))

        assert len(data["auditEvents"]) == 1
        assert data["auditEvents"][0] == {
            'acknowledged': False,
            'createdAt': mock.ANY,
            'data': {
                'update': {
                    'clarificationQuestionsOpen': False,
                    'framework': 'g-cloud',
                    'lots': [
                        'saas',
                        'paas',
                        'iaas',
                        'scs'
                    ],
                    'name': 'Example',
                    'slug': 'example',
                    'status': 'coming',
                    'hasDirectAward': True,
                    'hasFurtherCompetition': False,
                },
            },
            'id': mock.ANY,
            'links': {'self': 'http://127.0.0.1:5000/audit-events'},
            'objectId': framework_id,
            'objectType': 'Framework',
            'type': 'create_framework',
            'user': 'example',
        }

    def test_create_fails_if_framework_already_exists(self):
        self.client.post("/frameworks",
                         data=json.dumps(self.framework()),
                         content_type="application/json")

        response = self.client.post("/frameworks",
                                    data=json.dumps(self.framework()),
                                    content_type="application/json")

        assert response.status_code == 400
        assert json.loads(response.get_data(as_text=True))["error"] == "Slug 'example' already in use"

    def test_create_fails_if_status_is_invalid(self):
        response = self.client.post("/frameworks",
                                    data=json.dumps(self.framework(status="invalid")),
                                    content_type="application/json")

        assert response.status_code == 400
        assert json.loads(response.get_data(as_text=True))["error"] == "Invalid status value 'invalid'"

    def test_create_fails_if_clarification_questions_open_is_invalid(self):
        response = self.client.post("/frameworks",
                                    data=json.dumps(self.framework(clarificationQuestionsOpen="invalid")),
                                    content_type="application/json")

        assert response.status_code == 400
        assert json.loads(response.get_data(as_text=True))["error"] == "Invalid framework"

    def test_create_fails_if_lot_slug_is_invalid(self):
        response = self.client.post("/frameworks",
                                    data=json.dumps(self.framework(lots=["saas", "invalid", "bad"])),
                                    content_type="application/json")

        assert response.status_code == 400
        assert json.loads(response.get_data(as_text=True))["error"] == "Invalid lot slugs: bad, invalid"

    def test_create_fails_if_slug_is_invalid(self):
        response = self.client.post("/frameworks",
                                    data=json.dumps(self.framework(slug="this is/invalid")),
                                    content_type="application/json")

        assert response.status_code == 400
        assert json.loads(response.get_data(as_text=True))["error"] == "Invalid slug value 'this is/invalid'"

    def test_create_fails_if_direct_award_and_further_competition_false(self):
        framework = self.framework()
        framework['frameworks']['hasDirectAward'] = False
        framework['frameworks']['hasFurtherCompetition'] = False

        response = self.client.post("/frameworks",
                                    data=json.dumps(framework),
                                    content_type="application/json")

        assert response.status_code == 400
        assert json.loads(response.get_data(as_text=True))["error"] == "At least one of `hasDirectAward` or " \
                                                                       "`hasFurtherCompetition` must be True"

    def test_update_fails_if_direct_award_and_further_competition_both_false(self):
        framework = self.framework(slug='example')

        self.client.post("/frameworks", data=json.dumps(framework), content_type="application/json")

        framework = {'frameworks': {'hasDirectAward': False, 'hasFurtherCompetition': False}, 'updated_by': 'test'}
        response = self.client.post(f'/frameworks/example', data=json.dumps(framework), content_type='application/json')

        assert response.status_code == 400
        assert json.loads(response.get_data(as_text=True))["error"] == "At least one of `hasDirectAward` or " \
                                                                       "`hasFurtherCompetition` must be True"


class TestGetFramework(BaseApplicationTest):
    def test_a_single_framework_is_returned(self):
        response = self.client.get('/frameworks/g-cloud-7')
        data = json.loads(response.get_data())

        assert response.status_code == 200
        assert data['frameworks']['slug'] == 'g-cloud-7'
        assert 'status' in data['frameworks']

    def test_framework_lots_are_returned(self):
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
        response = self.client.get('/frameworks/biscuits-for-gov')

        assert response.status_code == 404


class TestUpdateFramework(BaseApplicationTest, JSONUpdateTestMixin, FixtureMixin):
    endpoint = '/frameworks/example'
    method = 'post'

    def setup(self):
        super(TestUpdateFramework, self).setup()

        self.framework_attributes_and_values_for_update = {
            'id': 1,
            'name': "Example Framework 2",
            'slug': "example-framework-2",
            'framework': "digital-outcomes-and-specialists",
            'family': "digital-outcomes-and-specialists",
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
                },
                "lotOrder": ['iaas', 'scs', 'saas', 'paas'],
            },
            'status': "standstill",
            'clarificationQuestionsOpen': False,
            'lots': ['saas', 'paas', 'iaas', 'scs'],
            'applicationsCloseAtUTC': '2023-04-11T16:00:00.000000Z',
            'intentionToAwardAtUTC': '2023-04-25T00:00:00.000000Z',
            'clarificationsCloseAtUTC': '2023-03-30T17:00:00.000000Z',
            'clarificationsPublishAtUTC': '2023-04-04T17:00:00.000000Z',
            'frameworkLiveAtUTC': '2023-05-01T00:00:00.000000Z',
            'frameworkExpiresAtUTC': '2024-04-30T00:00:00.000000Z',
            'allowDeclarationReuse': True,
            'hasDirectAward': True,
            'hasFurtherCompetition': False,
        }

        self.attribute_whitelist = FRAMEWORK_UPDATE_WHITELISTED_ATTRIBUTES_MAP.keys()

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

        for key, value in valid_attributes_and_values.items():
            response = self.post_framework_update({
                key: value
            })

            assert response.status_code == 200
            post_data = json.loads(response.get_data())['frameworks']

            # certain keys of `frameworkAgreementDetails` are un-nested and returned with other top-level keys
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    if nested_key in ("countersignerName", "frameworkAgreementVersion", "variations",):
                        assert post_data[nested_key] == nested_value

            assert post_data[key] == value

            # check the same data was actually persisted
            get_data = json.loads(
                self.client.get('/frameworks/example-framework').get_data()
            )['frameworks']
            assert post_data == get_data

    def test_adds_audit_event(self, live_example_framework):
        update_response = self.post_framework_update({'status': 'expired'})
        framework_id = json.loads(update_response.data)['frameworks']['id']

        audit_response = self.client.get("/audit-events")
        data = json.loads(audit_response.get_data(as_text=True))

        assert len(data["auditEvents"]) == 1
        assert data["auditEvents"][0] == {
            'acknowledged': False,
            'createdAt': mock.ANY,
            'data': {
                'frameworkSlug': 'example-framework',
                'update': {
                    'status': 'expired',
                },
                'framework_expires_at_utc set': "framework status set to 'expired'",
            },
            'id': mock.ANY,
            'links': {'self': 'http://127.0.0.1:5000/audit-events'},
            'objectId': framework_id,
            'objectType': 'Framework',
            'type': 'framework_update',
            'user': 'example user',
        }

    def test_cannot_update_non_whitelisted_fields(self, open_example_framework):
        invalid_attributes_and_values = {
            key: value for key, value in self.framework_attributes_and_values_for_update.items()
            if key not in self.attribute_whitelist
        }
        # add some random key
        invalid_attributes_and_values.update({'beverage': 'Clamato'})

        for key, value in invalid_attributes_and_values.items():
            response = self.post_framework_update({
                key: value
            })

            assert response.status_code == 400
            data = json.loads(response.get_data())['error']
            assert data == "Invalid keys for framework update: '{}'".format(key)

    def test_cannot_update_framework_with_invalid_status(self, open_example_framework):
        response = self.post_framework_update({
            'status': 'invalid'
        })

        assert response.status_code == 400
        data = json.loads(response.get_data())['error']
        assert 'Invalid status value' in data

    def test_passing_in_an_empty_update_is_a_failure(self, open_example_framework):
        response = self.post_framework_update({})

        assert response.status_code == 400
        data = json.loads(response.get_data())['error']
        assert data == "Framework update expects a payload"

    def test_schema_validation_for_framework_agreement_details(self, open_example_framework):
        invalid_framework_agreement_details = [
            # frameworkAgreementVersion should be a string
            {
                'variations': {},
                'frameworkAgreementVersion': 1,
            },
            # can't have a numeric lotDescription
            {
                'variations': {},
                'frameworkAgreementVersion': "1",
                'lotDescriptions': {"test-lot": 4321},
            },
            # can't have empty lotOrder
            {
                'variations': {},
                'frameworkAgreementVersion': "1",
                'lotOrder': [],
            },
            # frameworkAgreementVersion cannot be empty
            {
                'variations': {},
                'frameworkAgreementVersion': "",
            },
            # variations should be an object
            {
                'variations': 1,
                'frameworkAgreementVersion': "1.1.1",
            },
            # variations object must have 'createdAt' key
            {
                'frameworkAgreementVersion': "2",
                'variations': {"created_at": "today"},
            },
            # countersignerName cannot be empty
            {
                'variations': {},
                'frameworkAgreementVersion': "1",
                'countersignerName': "",
            },
            # invalid key
            {
                'variations': {},
                'frameworkAgreementVersion': "1",
                'frameworkAgreementDessert': "Portuguese tart",
            },
            # empty update
            {}
        ]

        for invalid_value in invalid_framework_agreement_details:
            response = self.post_framework_update({
                'frameworkAgreementDetails': invalid_value
            })
            assert response.status_code == 400

    @mock.patch('app.db.session.commit')
    def test_update_framework_catches_db_errors(self, db_commit, open_example_framework):
        db_commit.side_effect = IntegrityError("Could not commit", orig=None, params={})
        valid_attributes_and_values = {
            key: value for key, value in self.framework_attributes_and_values_for_update.items()
            if key in self.attribute_whitelist
        }

        for key, value in valid_attributes_and_values.items():
            response = self.post_framework_update({
                key: value
            })

            assert response.status_code == 400
            assert "Could not commit" in json.loads(response.get_data())["error"]

    def test_timestamps_set_on_state_change_with_audit_data(self, open_example_framework):
        updates = [
            {'clarificationQuestionsOpen': False},
            {'status': 'pending'},
            {'status': 'live'},
            {'status': 'expired'},
        ]
        timestamp_keys = [
            'clarificationsCloseAtUTC',
            'applicationsCloseAtUTC',
            'frameworkLiveAtUTC',
            'frameworkExpiresAtUTC'
        ]
        audit_data = [
            {'clarifications_close_at_utc set': 'clarification questions closed'},
            {'applications_close_at_utc set': "framework status set to 'pending'"},
            {'framework_live_at_utc set': "framework status set to 'live'"},
            {'framework_expires_at_utc set': "framework status set to 'expired'"},
        ]

        for update, timestamp_key, data in zip(updates, timestamp_keys, audit_data):
            update_timestamp = f'{datetime.datetime.utcnow().isoformat()}Z'
            with freeze_time(update_timestamp):
                self.post_framework_update(update)

            response = self.client.get('/frameworks/example-framework')
            framework = json.loads(response.get_data())['frameworks']
            assert framework[timestamp_key] == update_timestamp

            audit = AuditEvent.query.all()[-1]
            assert audit.data == {
                'frameworkSlug': 'example-framework',
                'update': update,
                **data,
            }

    def test_timestamps_not_updated_if_not_change_in_state(self, open_example_framework):
        updates = [
            {'clarificationQuestionsOpen': False},
            {'status': 'pending'},
            {'status': 'live'},
            {'status': 'expired'},
        ]
        timestamp_keys = [
            'clarificationsCloseAtUTC',
            'applicationsCloseAtUTC',
            'frameworkLiveAtUTC',
            'frameworkExpiresAtUTC'
        ]

        for update, timestamp_key in zip(updates, timestamp_keys):
            # Update the framework
            self.post_framework_update(update)
            check_time = datetime.datetime.utcnow()
            response = self.client.get('/frameworks/example-framework')
            framework = json.loads(response.get_data())['frameworks']
            timestamp = framework[timestamp_key]

            # Make sure a measurable amount of time has passed since last update
            assert datetime.datetime.utcnow() > check_time

            # Update the framework again, with the same values.
            self.post_framework_update(update)
            response = self.client.get('/frameworks/example-framework')
            framework = json.loads(response.get_data())['frameworks']

            # Make sure the timestamp hasn't changed.
            assert framework[timestamp_key] == timestamp


class TestFrameworkStats(BaseApplicationTest, FixtureMixin):
    def make_declaration(self, framework_id, supplier_ids, status=None):
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
        for supplier_id in supplier_ids:
            db.session.add(
                SupplierFramework(
                    framework_id=framework_id,
                    supplier_id=supplier_id,
                    declaration={}
                )
            )
        db.session.commit()

    def create_drafts(self, framework_id, supplier_id_counts):
        framework = Framework.query.get(framework_id)
        framework_lots = framework.lots
        for supplier_id, unsub_count, sub_count in supplier_id_counts:
            for ind, lot in zip(range(unsub_count + sub_count), cycle(framework_lots)):
                if lot.one_service_limit and ind >= len(framework_lots):
                    # skip creating second+ services for one_service_limit lots
                    continue

                db.session.add(
                    DraftService(
                        lot=lot,
                        framework_id=framework_id,
                        supplier_id=supplier_id,
                        data={},
                        status="not-submitted" if ind < unsub_count else "submitted",
                        lot_one_service_limit=lot.one_service_limit,
                    )
                )

        db.session.commit()

    def create_users(self, supplier_ids, logged_in_at):
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
        framework = Framework.query.filter(Framework.slug == framework_slug).first()

        self.register_framework_interest(framework.id, range(20))
        self.make_declaration(framework.id, [1, 3, 5, 7, 9, 11], status='started')
        self.make_declaration(framework.id, [0, 2, 4, 6, 8, 10], status='complete')

        self.create_drafts(framework.id, [
            (1, 1, 2),
            (2, 7, 15),
            (3, 2, 2),
            (14, 3, 7),
        ])

    def setup_data(self, framework_slug):
        self.setup_supplier_data()
        self.setup_framework_data(framework_slug)

    def test_stats(self):
        self.setup_supplier_data()
        self.setup_framework_data('g-cloud-7')
        self.setup_framework_data('digital-outcomes-and-specialists')

        response = self.client.get('/frameworks/g-cloud-7/stats')
        assert json.loads(response.get_data()) == {
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

                {u'count': 3, u'status': u'submitted',
                 u'declaration_made': False, u'lot': u'iaas'},
                {u'count': 3, u'status': u'submitted',
                 u'declaration_made': True, u'lot': u'iaas'},
                {u'count': 3, u'status': u'submitted',
                 u'declaration_made': False, u'lot': u'paas'},
                {u'count': 4, u'status': u'submitted',
                 u'declaration_made': True, u'lot': u'paas'},
                {u'count': 2, u'status': u'submitted',
                 u'declaration_made': False, u'lot': u'saas'},
                {u'count': 4, u'status': u'submitted',
                 u'declaration_made': True, u'lot': u'saas'},
                {u'count': 3, u'status': u'submitted',
                 u'declaration_made': False, u'lot': u'scs'},
                {u'count': 4, u'status': u'submitted',
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
        }

    def test_stats_are_for_g_cloud_7_only(self):
        self.setup_data('g-cloud-6')
        response = self.client.get('/frameworks/g-cloud-7/stats')
        assert json.loads(response.get_data()) == {
            u'interested_suppliers': [],
            u'services': [],
            u'supplier_users': [
                {u'count': 4, u'recent_login': False},
                {u'count': 2, u'recent_login': None},
                {u'count': 5, u'recent_login': True},
            ]
        }

    def test_stats_handles_null_declarations(self):
        self.setup_data('g-cloud-7')
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


class TestGetFrameworkSuppliers(BaseApplicationTest, FixtureMixin):
    def setup(self):
        """Sets up supplier frameworks as follows:

        Suppliers with IDs 0-10 have a G-Cloud 8 SupplierFramework record ("have registered interest")
        Supplier 0 has returned a G-Cloud 7 agreement but not G-Cloud 8
        Suppliers 1 and 2 have drafts of G-Cloud 8 agreements
        Suppliers 3, 4 and 5 have returned their G-Cloud 8 agreements
        Supplier 4 and 9's agreements were put on hold
        Supplier 6's has been approved for countersignature but doesn't have a file yet
        Suppliers 7, 8, 9 and 10 have countersigned agreements
        Supplier 11 has nothing to do with anything or anyone

        We use freeze_time to create a non-trivial ordering of creation/signing events in time, so that different
        suppliers event timelines overlap in slightly complex ways, ensuring we test things like ordering properly.
        """
        super(TestGetFrameworkSuppliers, self).setup()

        with freeze_time("2016-10-09", tick=True):
            self.setup_dummy_suppliers(12)
            self.setup_dummy_user(id=123, role='supplier')
            self.setup_dummy_user(id=321, role='admin-ccs-sourcing')

        db.session.execute("UPDATE frameworks SET status='open' WHERE slug='g-cloud-7'")
        db.session.execute("UPDATE frameworks SET status='open' WHERE slug='g-cloud-8'")
        db.session.commit()

        with freeze_time("2016-10-10", tick=True):
            # Supplier zero is on G-Cloud 7
            response = self.client.put(
                '/suppliers/0/frameworks/g-cloud-7',
                data=json.dumps({
                    'updated_by': 'example'
                }),
                content_type='application/json')
            assert response.status_code == 201, response.get_data(as_text=True)

            response = self.client.post(
                '/suppliers/0/frameworks/g-cloud-7',
                data=json.dumps({
                    'updated_by': 'example',
                    'frameworkInterest': {'onFramework': True}
                }),
                content_type='application/json')
            assert response.status_code == 200, response.get_data(as_text=True)

            response = self.client.post(
                '/agreements',
                data=json.dumps({
                    'updated_by': 'example',
                    'agreement': {'supplierId': 0, 'frameworkSlug': 'g-cloud-7'},
                }),
                content_type='application/json')
            assert response.status_code == 201, response.get_data(as_text=True)
            data = json.loads(response.get_data())
            agreement_id = data['agreement']['id']

            response = self.client.post(
                '/agreements/{}'.format(agreement_id),
                data=json.dumps({
                    'updated_by': 'example',
                    'agreement': {'signedAgreementPath': '/path-to-g-cloud-7.pdf'},
                }),
                content_type='application/json')
            assert response.status_code == 200, response.get_data(as_text=True)

            response = self.client.post(
                '/agreements/{}/sign'.format(agreement_id),
                data=json.dumps({
                    'updated_by': 'example',
                    'agreement': {},
                }),
                content_type='application/json')
            assert response.status_code == 200, response.get_data(as_text=True)

        # (Almost) everyone is on G-Cloud 8
        for supplier_id in range(11):
            with freeze_time(datetime.datetime(2016, 10, supplier_id + 2)):
                response = self.client.put(
                    '/suppliers/{}/frameworks/g-cloud-8'.format(supplier_id),
                    data=json.dumps({
                        'updated_by': 'example'
                    }),
                    content_type='application/json')
                assert response.status_code == 201, response.get_data(as_text=True)

            with freeze_time(datetime.datetime(2016, 10, supplier_id + 2, 10)):
                response = self.client.put(
                    '/suppliers/{}/frameworks/g-cloud-8/declaration'.format(supplier_id),
                    data=json.dumps({
                        'updated_by': 'example',
                        'declaration': {
                            "status": "complete",
                            "firstRegistered": "16/06/1904",
                        },
                    }),
                    content_type='application/json')
                assert response.status_code == 201, response.get_data(as_text=True)

            with freeze_time(datetime.datetime(2016, 10, supplier_id + 3)):
                response = self.client.post(
                    '/suppliers/{}/frameworks/g-cloud-8'.format(supplier_id),
                    data=json.dumps({
                        'updated_by': 'example',
                        'frameworkInterest': {
                            'onFramework': True,
                        },
                    }),
                    content_type='application/json')
                assert response.status_code == 200, response.get_data(as_text=True)

        # Suppliers 1-10 have started to return a G-Cloud 8 agreement (created a draft)
        agreement_ids = {}
        for supplier_id in range(1, 11):
            with freeze_time(datetime.datetime(2016, 11, (supplier_id + 1) * 2)):
                response = self.client.post(
                    '/agreements',
                    data=json.dumps({
                        'updated_by': 'example',
                        'agreement': {'supplierId': supplier_id, 'frameworkSlug': 'g-cloud-8'},
                    }),
                    content_type='application/json'
                )
                assert response.status_code == 201, response.get_data(as_text=True)
                data = json.loads(response.get_data())
                agreement_ids[supplier_id] = data['agreement']['id']

        # (supplier 10 created a superfluous agreement which they then didn't use
        with freeze_time(datetime.datetime(2016, 11, 26)):
            response = self.client.post(
                '/agreements',
                data=json.dumps({
                    'updated_by': 'example',
                    'agreement': {'supplierId': 10, 'frameworkSlug': 'g-cloud-8'},
                }),
                content_type='application/json'
            )
            assert response.status_code == 201, response.get_data(as_text=True)

        for supplier_id in range(1, 11):
            with freeze_time(datetime.datetime(2016, 11, (supplier_id + 1) * 2, 10)):
                response = self.client.post(
                    '/agreements/{}'.format(agreement_ids[supplier_id]),
                    data=json.dumps({
                        'updated_by': 'example',
                        'agreement': {
                            'signedAgreementPath': 'path/to/agreement/{}.pdf'.format(supplier_id),
                            'signedAgreementDetails': {
                                'signerName': 'name_{}'.format(supplier_id),
                                'signerRole': 'job_{}'.format(supplier_id)
                            },
                        }
                    }),
                    content_type='application/json'
                )
                assert response.status_code == 200, response.get_data(as_text=True)

        # Suppliers 3-10 have returned their G-Cloud 8 agreement
        for supplier_id in range(3, 11):
            with freeze_time(datetime.datetime(2016, 11, 30, 11 - supplier_id)):
                response = self.client.post(
                    '/agreements/{}/sign'.format(agreement_ids[supplier_id]),
                    data=json.dumps({
                        'updated_by': 'example',
                        'agreement': {
                            'signedAgreementDetails': {
                                'uploaderUserId': 123,
                            },
                        },
                    }),
                    content_type='application/json'
                )
                assert response.status_code == 200, response.get_data(as_text=True)

        # Supplier 4 and 9's agreements were put on hold (only 4 subsequently remained on hold)
        for supplier_id in (4, 9,):
            with freeze_time(datetime.datetime(2016, 11, 30, 12 - (supplier_id // 3))):
                response = self.client.post(
                    '/agreements/{}/on-hold'.format(agreement_ids[supplier_id]),
                    data=json.dumps({'updated_by': 'example'}),
                    content_type='application/json'
                )
                assert response.status_code == 200, response.get_data(as_text=True)

        # Suppliers 6-10 have been approved for countersignature
        for supplier_id in range(6, 11):
            with freeze_time(datetime.datetime(2016, 11, 30, 15 - supplier_id)):
                response = self.client.post(
                    '/agreements/{}/approve'.format(agreement_ids[supplier_id]),
                    data=json.dumps({
                        'updated_by': 'example',
                        "agreement": {'userId': 321},
                    }),
                    content_type='application/json'
                )
                assert response.status_code == 200, response.get_data(as_text=True)

        # Suppliers 7-10 have countersigned agreements
        for supplier_id in range(7, 11):
            with freeze_time(datetime.datetime(2016, 12, 25, 5 + supplier_id)):
                response = self.client.post(
                    '/agreements/{}'.format(agreement_ids[supplier_id]),
                    data=json.dumps({
                        'updated_by': 'example',
                        'agreement': {
                            'countersignedAgreementPath': 'path/to/countersigned{}.pdf'.format(supplier_id)
                        }
                    }),
                    content_type='application/json'
                )
                assert response.status_code == 200, response.get_data(as_text=True)

    def test_list_suppliers_combined(self, live_g8_framework):
        # it would be nice to implement the following as individual tests, but the setup method is too expensive and has
        # a detrimental effect on testrun time. since this is a readonly endpoint we shouldn't me mutating state between
        # calls anyway, and we're always testing the same state setup by the same setup routine, so a quick fix for now
        # is to merge these into a combined supertest. they are still kept apart as separate methods to avoid locals
        # leaking from one test to another and disguising broken tests.
        # TODO perhaps fix db global teardown fixture so that db isn't mandatorily cleared after every test, allowing
        # us to use shared-setup fixtures.
        self._subtest_list_suppliers_related_to_a_framework()
        self._subtest_list_suppliers_by_agreement_returned_false()
        self._subtest_list_suppliers_by_agreement_returned_true()
        self._subtest_list_suppliers_by_agreement_returned_false()
        self._subtest_list_suppliers_by_status_signed()
        self._subtest_list_suppliers_by_status_on_hold()
        self._subtest_list_suppliers_by_status_approved()
        self._subtest_list_suppliers_by_status_countersigned()
        self._subtest_list_suppliers_by_multiple_statuses_1()
        self._subtest_list_suppliers_by_multiple_statuses_2()
        self._subtest_list_suppliers_by_multiple_statuses_and_agreement_returned_true()
        self._subtest_list_suppliers_by_multiple_statuses_and_agreement_returned_false()

    def _subtest_list_suppliers_related_to_a_framework(self):
        # One G7 supplier
        response = self.client.get('/frameworks/g-cloud-7/suppliers')
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert tuple(sf["supplierId"] for sf in data["supplierFrameworks"]) == (0,)
        assert not any(
            (sf.get("agreementDetails") or {}).get("uploaderUserEmail") for sf in data["supplierFrameworks"]
        )
        # Ten G8 suppliers
        response = self.client.get('/frameworks/g-cloud-8/suppliers?with_users=true')
        assert response.status_code == 200
        data = json.loads(response.get_data())

        # supplierFrameworks are returned in order of ID if they don't have a framework agreement
        # returned, and from oldest to newest returned if they do
        assert tuple(sf["supplierId"] for sf in data["supplierFrameworks"]) == (0, 1, 2, 10, 9, 8, 7, 6, 5, 4, 3,)
        # this listing view should not include extended user information
        assert not any(
            (sf.get("agreementDetails") or {}).get("uploaderUserEmail") for sf in data["supplierFrameworks"]
        )
        assert all(sf['declaration'] for sf in data['supplierFrameworks'])

    def _subtest_list_suppliers_by_agreement_returned_true(self):
        response = self.client.get(
            '/frameworks/g-cloud-8/suppliers?with_users=false&agreement_returned=true'
        )

        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert tuple(sf["supplierId"] for sf in data["supplierFrameworks"]) == (10, 9, 8, 7, 6, 5, 4, 3,)
        assert all(sf["agreementReturnedAt"] for sf in data["supplierFrameworks"])
        assert all(sf['declaration'] for sf in data['supplierFrameworks'])

    def _subtest_list_suppliers_by_agreement_returned_false(self):
        response = self.client.get(
            '/frameworks/g-cloud-8/suppliers?agreement_returned=false'
        )

        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert tuple(sf["supplierId"] for sf in data["supplierFrameworks"]) == (0, 1, 2,)
        assert all(sf['agreementReturnedAt'] is None for sf in data['supplierFrameworks'])
        assert all(sf['declaration'] for sf in data['supplierFrameworks'])

    def _subtest_list_suppliers_by_status_signed(self):
        response = self.client.get('/frameworks/g-cloud-8/suppliers?status=signed&with_declarations=false')

        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert tuple(sf["supplierId"] for sf in data["supplierFrameworks"]) == (5, 3,)
        assert all(sf['agreementStatus'] == "signed" for sf in data['supplierFrameworks'])
        assert not any('declaration' in sf for sf in data['supplierFrameworks'])

    def _subtest_list_suppliers_by_status_on_hold(self):
        response = self.client.get('/frameworks/g-cloud-8/suppliers?status=on-hold')

        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert tuple(sf["supplierId"] for sf in data["supplierFrameworks"]) == (4,)
        assert all(sf['agreementStatus'] == "on-hold" for sf in data['supplierFrameworks'])
        assert all(sf['declaration'] for sf in data['supplierFrameworks'])

    def _subtest_list_suppliers_by_status_approved(self):
        response = self.client.get('/frameworks/g-cloud-8/suppliers?status=approved')

        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert tuple(sf["supplierId"] for sf in data["supplierFrameworks"]) == (6,)
        assert all(sf['agreementStatus'] == "approved" for sf in data['supplierFrameworks'])
        assert all(sf['declaration'] for sf in data['supplierFrameworks'])

    def _subtest_list_suppliers_by_status_countersigned(self):
        response = self.client.get('/frameworks/g-cloud-8/suppliers?status=countersigned')

        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert tuple(sf["supplierId"] for sf in data["supplierFrameworks"]) == (10, 9, 8, 7,)
        assert all(sf['agreementStatus'] == "countersigned" for sf in data['supplierFrameworks'])
        assert all(sf['declaration'] for sf in data['supplierFrameworks'])

    def _subtest_list_suppliers_by_multiple_statuses_1(self):
        response = self.client.get('/frameworks/g-cloud-8/suppliers?status=approved,countersigned&with_users=true')

        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert tuple(sf["supplierId"] for sf in data["supplierFrameworks"]) == (10, 9, 8, 7, 6,)
        assert all(sf['agreementStatus'] in ("approved", "countersigned") for sf in data['supplierFrameworks'])
        assert all(sf['declaration'] for sf in data['supplierFrameworks'])

    def _subtest_list_suppliers_by_multiple_statuses_2(self):
        response = self.client.get('/frameworks/g-cloud-8/suppliers?with_declarations=true&status=signed,approved')

        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert tuple(sf["supplierId"] for sf in data["supplierFrameworks"]) == (6, 5, 3,)
        assert all(sf['agreementStatus'] in ("approved", "signed") for sf in data['supplierFrameworks'])
        assert all(sf['declaration'] for sf in data['supplierFrameworks'])

    def _subtest_list_suppliers_by_multiple_statuses_and_agreement_returned_true(self):
        response = self.client.get(
            '/frameworks/g-cloud-8/suppliers?status=approved,countersigned&agreement_returned=true'
        )

        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert tuple(sf["supplierId"] for sf in data["supplierFrameworks"]) == (10, 9, 8, 7, 6,)
        assert all(sf['agreementStatus'] in ("approved", "countersigned") for sf in data['supplierFrameworks'])
        assert all(sf["agreementReturnedAt"] for sf in data["supplierFrameworks"])
        assert all(sf['declaration'] for sf in data['supplierFrameworks'])

    def _subtest_list_suppliers_by_multiple_statuses_and_agreement_returned_false(self):
        response = self.client.get(
            '/frameworks/g-cloud-8/suppliers?status=approved,countersigned&agreement_returned=false'
        )

        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert len(data['supplierFrameworks']) == 0


class TestGetFrameworkInterest(BaseApplicationTest, FixtureMixin):
    def setup(self):
        super(TestGetFrameworkInterest, self).setup()

        self.register_g7_interest(5)

    def register_g7_interest(self, num):
        self.setup_dummy_suppliers(num)
        for supplier_id in range(num):
            db.session.add(
                SupplierFramework(
                    framework_id=4,
                    supplier_id=supplier_id
                )
            )
        db.session.commit()

    def test_interested_suppliers_are_returned(self):
        response = self.client.get('/frameworks/g-cloud-7/interest')

        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert data['interestedSuppliers'] == [0, 1, 2, 3, 4]

    def test_a_404_is_raised_if_it_does_not_exist(self):
        response = self.client.get('/frameworks/biscuits-for-gov/interest')

        assert response.status_code == 404


class TestTransitionDosFramework(BaseApplicationTest, FixtureMixin):
    def _setup_for_succesful_call(self):
        self.setup_dummy_framework(
            slug="digital-outcomes-and-specialists-2", framework_family="digital-outcomes-and-specialists",
            status='live', id=101,
        )
        self.setup_dummy_framework(
            slug="digital-outcomes-and-specialists-3", framework_family="digital-outcomes-and-specialists",
            status='standstill', id=102,
        )
        self.setup_dummy_user()
        for status in ("draft", "live", "withdrawn", "closed", "draft", "cancelled", "unsuccessful"):
            self.setup_dummy_brief(
                status=status,
                framework_slug="digital-outcomes-and-specialists-2",
                data={"some": "data"},
                user_id=123,
            )

    def test_400s_if_invalid_updater_json(self):
        response = self.client.post(
            "/frameworks/transition-dos/sausage-cloud-6",
            data=json.dumps({"not-updated": "correctly"}),
            content_type="application/json"
        )
        data = response.get_data(as_text=True)

        assert response.status_code == 400
        assert json.loads(data)['error'] == "JSON validation error: 'updated_by' is a required property"

    def test_400s_if_expiring_framework_not_in_request_body(self):
        response = self.client.post(
            "/frameworks/transition-dos/sausage-cloud-6",
            data=json.dumps({"updated_by": "🤖"}),
            content_type="application/json"
        )
        data = response.get_data(as_text=True)

        assert response.status_code == 400
        assert json.loads(data)['error'] == "Invalid JSON must have 'expiringFramework' keys"

    def test_400s_if_going_live_framework_is_older_than_expiring_framework(self):
        dos_2_id = self.setup_dummy_framework(
            slug="digital-outcomes-and-specialists-2", framework_family="digital-outcomes-and-specialists", id=101,
        )

        response = self.client.post(
            "/frameworks/transition-dos/digital-outcomes-and-specialists",
            data=json.dumps({
                "updated_by": "🤖",
                "expiringFramework": "digital-outcomes-and-specialists-2",
            }),
            content_type="application/json"
        )
        data = response.get_data(as_text=True)

        assert response.status_code == 400
        assert json.loads(data)['error'] == \
            f"'going_live_framework' ID ('5') must greater than'expiring_framework' ID ('{dos_2_id}')"

    @pytest.mark.parametrize(
        ("going_live_slug", "going_live_family", "expiring_slug", "expiring_family"),
        (
            ("g-cloud-10", "g-cloud", "digital-outcomes-and-specialists", "digital-outcomes-and-specialists",),
            ("digital-outcomes-and-specialists-2", "digital-outcomes-and-specialists", "g-cloud-10", "g-cloud",)
        )
    )
    def test_400s_if_either_framework_has_wrong_family(
        self, going_live_slug, going_live_family, expiring_slug, expiring_family,
    ):
        self.setup_dummy_framework(
            slug="g-cloud-10", framework_family="g-cloud", lots=[], id=101,
        )
        self.setup_dummy_framework(
            slug="digital-outcomes-and-specialists-2", framework_family="digital-outcomes-and-specialists", id=102,
        )

        response = self.client.post(
            f"/frameworks/transition-dos/{going_live_slug}",
            data=json.dumps({
                "updated_by": "🤖",
                "expiringFramework": f"{expiring_slug}",
            }),
            content_type="application/json"
        )
        data = response.get_data(as_text=True)

        assert response.status_code == 400
        assert json.loads(data)['error'] == f"'going_live_framework' family: '{going_live_family}' and " \
            f"'expiring_framework' family: '{expiring_family}' must both be 'digital-outcomes-and-specialists'"

    @pytest.mark.parametrize('status', ('coming', 'open', 'pending', 'live', 'expired'))
    def test_400s_if_going_live_framework_status_is_not_standstill(self, status):
        self.setup_dummy_framework(
            slug="digital-outcomes-and-specialists-2", framework_family="digital-outcomes-and-specialists",
            status='live', id=101,
        )
        self.setup_dummy_framework(
            slug="digital-outcomes-and-specialists-3", framework_family="digital-outcomes-and-specialists",
            status=status, id=102,
        )

        response = self.client.post(
            "/frameworks/transition-dos/digital-outcomes-and-specialists-3",
            data=json.dumps({
                "updated_by": "🤖",
                "expiringFramework": "digital-outcomes-and-specialists-2",
            }),
            content_type="application/json"
        )
        data = response.get_data(as_text=True)

        assert response.status_code == 400
        assert json.loads(data)['error'] == f"'going_live_framework' status ({status}) must be 'standstill', and " \
            "'expiring_framework' status (live) must be 'live'"

    def test_success_does_all_the_right_things(self):
        # Remove all audit events to make assertions easier later
        AuditEvent.query.delete()
        self._setup_for_succesful_call()

        # keep track of brief ids for assertions later
        draft_brief_ids = {
            brief.id for brief in Brief.query.filter(Brief.framework_id == 101).all() if brief.status == 'draft'
        }
        assert len(draft_brief_ids) == 2

        not_draft_brief_ids = {
            brief.id for brief in Brief.query.filter(Brief.framework_id == 101).all() if brief.status != 'draft'
        }
        assert len(not_draft_brief_ids) == 5

        with freeze_time('2018-09-03 17:09:56.999999'):
            response = self.client.post(
                "/frameworks/transition-dos/digital-outcomes-and-specialists-3",
                data=json.dumps({
                    "updated_by": "🤖",
                    "expiringFramework": "digital-outcomes-and-specialists-2",
                }),
                content_type="application/json"
            )

        assert response.status_code == 200

        # Assert that the correct briefs were transferred to the new live framework
        expired_framework_briefs = Brief.query.filter(Brief.framework_id == 101).all()
        new_live_framework_briefs = Brief.query.filter(Brief.framework_id == 102).all()

        assert all(brief.status == "draft" for brief in new_live_framework_briefs)
        assert {brief.id for brief in new_live_framework_briefs} == draft_brief_ids

        assert all(brief.status != "draft" for brief in expired_framework_briefs)
        assert {brief.id for brief in expired_framework_briefs} == not_draft_brief_ids

        # Assert audit events were created for the brief changes
        brief_audits = AuditEvent.query.filter(AuditEvent.type == "update_brief_framework_id").all()
        assert len(brief_audits) == 2
        assert all(
            (audit.data["previousFrameworkId"], audit.data["newFrameworkId"]) == (101, 102) for audit in brief_audits
        )
        assert {audit.data["briefId"] for audit in brief_audits} == draft_brief_ids

        # Assert the frameworks statuses were correctly changed and timestamps set
        expired_framework = Framework.query.get(101)
        new_live_framework = Framework.query.get(102)
        assert expired_framework.status == "expired"
        assert expired_framework.framework_expires_at_utc == datetime.datetime(2018, 9, 3, 17, 9, 56, 999999)
        assert new_live_framework.status == "live"
        assert new_live_framework.framework_live_at_utc == datetime.datetime(2018, 9, 3, 17, 9, 56, 999999)

        # Assert audit events for the framework updates were created
        framework_audits = AuditEvent.query.filter(AuditEvent.type == "framework_update").all()
        assert len(framework_audits) == 2
        assert {(audit.data["update"]["status"], audit.data["frameworkSlug"]) for audit in framework_audits} == \
            {("expired", "digital-outcomes-and-specialists-2"), ("live", "digital-outcomes-and-specialists-3")}

        # Assert the endpoint returns the new live framework to us
        assert json.loads(response.get_data(as_text=True))["frameworks"]["slug"] == "digital-outcomes-and-specialists-3"

    def test_audit_events_have_corresponding_timestamps(self):
        AuditEvent.query.delete()
        self._setup_for_succesful_call()

        response = self.client.post(
            "/frameworks/transition-dos/digital-outcomes-and-specialists-3",
            data=json.dumps({
                "updated_by": "🤖",
                "expiringFramework": "digital-outcomes-and-specialists-2",
            }),
            content_type="application/json"
        )

        assert response.status_code == 200

        framework_audit_events = AuditEvent.query.filter(AuditEvent.type == "framework_update").all()
        assert all(audit.created_at == framework_audit_events[0].created_at for audit in framework_audit_events)

        brief_audit_events = AuditEvent.query.filter(AuditEvent.type == "update_brief_framework_id").all()
        assert all(audit.created_at == brief_audit_events[0].created_at for audit in brief_audit_events)

    @pytest.mark.parametrize('commit_to_fail_on', ('frameworks', 'briefs'))
    def test_integrity_errors_are_handled_and_changes_rolled_back(self, commit_to_fail_on):
        from app.main.views.frameworks import db as app_db
        commit_func = app_db.session.commit

        # Using a generator here so that `commit_func` gets called when the commit mock is called, and not before.
        def _side_effects(commit_to_fail_on):
            if commit_to_fail_on == 'briefs':
                yield commit_func()
            raise IntegrityError("Could not commit", orig=None, params={})

        self._setup_for_succesful_call()

        with mock.patch("app.main.views.frameworks.db.session.commit") as commit_mock:
            commit_mock.side_effect = _side_effects(commit_to_fail_on)
            response = self.client.post(
                "/frameworks/transition-dos/digital-outcomes-and-specialists-3",
                data=json.dumps({
                    "updated_by": "🤖",
                    "expiringFramework": "digital-outcomes-and-specialists-2",
                }),
                content_type="application/json"
            )
        data = response.get_data(as_text=True)

        assert response.status_code == 400
        assert "Could not commit" in json.loads(data)["error"]

        expiring_framework_briefs = Brief.query.filter(Brief.framework_id == 101).all()
        going_live_framework_briefs = Brief.query.filter(Brief.framework_id == 102).all()

        assert len(expiring_framework_briefs) == 7
        assert not going_live_framework_briefs

        if commit_to_fail_on == 'frameworks':
            assert Framework.query.get(101).status == "live"
            assert Framework.query.get(102).status == "standstill"
        else:
            assert Framework.query.get(101).status == "expired"
            assert Framework.query.get(102).status == "live"
