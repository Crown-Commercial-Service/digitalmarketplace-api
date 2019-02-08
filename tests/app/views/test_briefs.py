import json
from datetime import datetime
from datetime import timedelta
import pendulum

import mock
from ..helpers import BaseApplicationTest, COMPLETE_DIGITAL_SPECIALISTS_BRIEF

from dmapiclient.audit import AuditTypes
from app import db
from app.models import Brief, Framework


class TestBriefs(BaseApplicationTest):
    def setup(self):
        super(TestBriefs, self).setup()
        self.user_id = self.setup_dummy_user(role='buyer')

        with self.app.app_context():
            framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
            self._original_framework_status = framework.status
            framework.status = 'live'

            db.session.add(framework)
            db.session.commit()

    def teardown(self):
        with self.app.app_context():
            framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
            framework.status = self._original_framework_status

            db.session.add(framework)
            db.session.commit()
        super(TestBriefs, self).teardown()

    def test_create_brief_with_no_data(self):
        res = self.client.post(
            '/briefs',
            content_type='application/json')

        assert res.status_code == 400

    def test_create_brief(self):
        res = self.client.post(
            '/briefs',
            data=json.dumps({
                'briefs': {
                    'userId': self.user_id,
                    'frameworkSlug': 'digital-outcomes-and-specialists',
                    'lot': 'digital-specialists',
                    'title': 'the title',
                },
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 201, res.get_data(as_text=True)
        assert data['briefs']['frameworkSlug'] == 'digital-outcomes-and-specialists'
        assert data['briefs']['title'] == 'the title'

    def test_create_fails_if_lot_does_not_require_briefs(self):
        res = self.client.post(
            '/briefs',
            data=json.dumps({
                'briefs': {
                    'userId': self.user_id,
                    'frameworkSlug': 'digital-outcomes-and-specialists',
                    'lot': 'user-research-studios',
                    'title': 'the title',
                },
                'update_details': {
                    'updated_by': 'example'
                }
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == "Lot 'User research studios' does not require a brief"

    def test_create_fails_if_required_field_is_not_provided(self):
        res = self.client.post(
            '/briefs',
            data=json.dumps({
                'briefs': {
                    'userId': self.user_id,
                    'frameworkSlug': 'digital-outcomes-and-specialists',
                    'lot': 'digital-specialists',
                },
                'updated_by': 'example',
                'page_questions': ['title'],
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == {'title': 'answer_required'}

    def test_can_only_create_briefs_on_live_frameworks(self):
        with self.app.app_context():
            framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
            self._original_framework_status = framework.status
            framework.status = 'open'

            db.session.add(framework)
            db.session.commit()

        res = self.client.post(
            '/briefs',
            data=json.dumps({
                'briefs': {
                    'userId': self.user_id,
                    'frameworkSlug': 'digital-outcomes-and-specialists',
                    'lot': 'digital-specialists',
                    'title': 'the title',
                },
                'update_details': {
                    'updated_by': 'example'
                }
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == 'Framework must be live'

    def test_create_brief_creates_audit_event(self):
        self.client.post(
            '/briefs',
            data=json.dumps({
                'briefs': {
                    'userId': self.user_id,
                    'frameworkSlug': 'digital-outcomes-and-specialists',
                    'lot': 'digital-specialists',
                    'title': 'my title',
                },
                'updated_by': 'example'
            }),
            content_type='application/json')

        audit_response = self.client.get('/audit-events')
        assert audit_response.status_code == 200
        data = json.loads(audit_response.get_data(as_text=True))

        brief_audits = [event for event in data['auditEvents'] if event['type'] == AuditTypes.create_brief.value]
        assert len(brief_audits) == 1
        assert brief_audits[0]['data'] == {
            'briefId': mock.ANY,
            'briefJson': {
                'frameworkSlug': 'digital-outcomes-and-specialists',
                'lot': 'digital-specialists',
                'title': 'my title'
            }
        }

    def test_create_brief_fails_if_schema_validation_fails(self):
        res = self.client.post(
            '/briefs',
            data=json.dumps({
                'briefs': {
                    'userId': self.user_id,
                    'frameworkSlug': 'digital-outcomes-and-specialists',
                    'lot': 'digital-specialists',
                    'title': 'my title' * 30,
                },
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == {'title': 'under_character_limit'}

    def test_create_brief_fails_if_user_does_not_exist(self):
        res = self.client.post(
            '/briefs',
            data=json.dumps({
                'briefs': {
                    'userId': 999,
                    'frameworkSlug': 'digital-outcomes-and-specialists',
                    'lot': 'digital-specialists',
                },
                'updated_by': 'example'
            }),
            content_type='application/json')

        assert res.status_code == 400
        assert json.loads(res.get_data(as_text=True))['error'] == 'User ID does not exist'

    def test_create_brief_fails_if_framework_does_not_exist(self):
        res = self.client.post(
            '/briefs',
            data=json.dumps({
                'briefs': {
                    'userId': self.user_id,
                    'frameworkSlug': 'not-exists',
                    'lot': 'digital-specialists',
                },
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')

        assert res.status_code == 400
        assert json.loads(res.get_data(as_text=True))['error'] == "Framework 'not-exists' does not exist"

    def test_create_brief_fails_if_lot_does_not_exist(self):
        res = self.client.post(
            '/briefs',
            data=json.dumps({
                'briefs': {
                    'userId': self.user_id,
                    'frameworkSlug': 'digital-outcomes-and-specialists',
                    'lot': 'not-exists',
                },
                'updated_by': 'example'
            }),
            content_type='application/json')

        assert res.status_code == 400
        assert json.loads(res.get_data(as_text=True))['error'] == \
            "Incorrect lot 'not-exists' for framework 'digital-outcomes-and-specialists'"

    def test_update_brief(self):
        self.setup_dummy_briefs(1)

        res = self.client.post(
            '/briefs/1',
            data=json.dumps({
                'briefs': {'title': 'my title'},
                'update_details': {'updated_by': 'example'},
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['briefs']['title'] == 'my title'

    def test_update_fails_if_required_field_is_not_provided(self):
        self.setup_dummy_briefs(1)

        res = self.client.post(
            '/briefs/1',
            data=json.dumps({
                'briefs': {},
                'updated_by': 'example',
                'page_questions': ['title'],
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == {'title': 'answer_required'}

    def test_update_fails_if_status_is_live(self):
        self.setup_dummy_briefs(1, status='live')

        res = self.client.post(
            '/briefs/1',
            data=json.dumps({
                'briefs': {'title': 'my title'},
                'update_details': {'updated_by': 'example'},
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == 'Cannot update a live brief'

    def test_update_fails_if_status_is_closed(self):
        self.setup_dummy_briefs(1, status='closed')

        res = self.client.post(
            '/briefs/1',
            data=json.dumps({
                'briefs': {'title': 'my title'},
                'update_details': {'updated_by': 'example'},
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == 'Cannot update a closed brief'

    def test_update_brief_creates_audit_event(self):
        self.setup_dummy_briefs(1)

        self.client.post(
            '/briefs/1',
            data=json.dumps({
                'briefs': {'title': 'my title'},
                'updated_by': 'example'
            }),
            content_type='application/json')

        audit_response = self.client.get('/audit-events')
        assert audit_response.status_code == 200
        data = json.loads(audit_response.get_data(as_text=True))

        brief_audits = [event for event in data['auditEvents'] if event['type'] == AuditTypes.update_brief.value]
        assert len(brief_audits) == 1
        assert brief_audits[0]['data'] == {'briefId': 1, 'briefJson': {'title': 'my title'}}

    def test_update_brief_fails_if_schema_validation_fails(self):
        self.setup_dummy_briefs(1)

        res = self.client.post(
            '/briefs/1',
            data=json.dumps({
                'briefs': {
                    'title': 'my title' * 30,
                },
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == {'title': 'under_character_limit'}

    def test_update_brief_criteria_weightings(self):
        self.setup_dummy_briefs(1)

        res = self.client.post(
            '/briefs/1',
            data=json.dumps({
                'briefs': {'technicalWeighting': 68, 'culturalWeighting': 7, 'priceWeighting': 25},
                'update_details': {'updated_by': 'example'},
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['briefs']['technicalWeighting'] == 68

    def test_update_brief_criteria_validation_weighting_sums_are_100(self):
        self.setup_dummy_briefs(1)

        res = self.client.post(
            '/briefs/1',
            data=json.dumps({
                'briefs': {'technicalWeighting': 10, 'culturalWeighting': 20, 'priceWeighting': 71},
                'update_details': {'updated_by': 'example'},
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == {
            "technicalWeighting": "total_should_be_100",
            "culturalWeighting": "total_should_be_100",
            "priceWeighting": "total_should_be_100"
        }

    def test_update_brief_criteria_validation_of_maximums_and_minimums(self):
        self.setup_dummy_briefs(1)

        res = self.client.post(
            '/briefs/1',
            data=json.dumps({
                'briefs': {'technicalWeighting': 15, 'culturalWeighting': 105, 'priceWeighting': -1},
                'update_details': {'updated_by': 'example'},
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        # cultural weighting of 75 above the maximum
        # price weighting of 10 is below the minimum
        assert data['error'] == {
            "culturalWeighting": "not_a_number",
            "priceWeighting": "not_a_number"
        }

    def test_update_brief_criteria_validation_of_non_integers(self):
        self.setup_dummy_briefs(1)

        res = self.client.post(
            '/briefs/1',
            data=json.dumps({
                'briefs': {'technicalWeighting': 'fifteen', 'culturalWeighting': '', 'priceWeighting': 30},
                'update_details': {'updated_by': 'example'},
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == {
            "technicalWeighting": "not_a_number",
            "culturalWeighting": "not_a_number"
        }

    def test_update_brief_returns_404_if_not_found(self):
        res = self.client.post(
            '/briefs/1',
            data=json.dumps({
                'briefs': {},
                'updated_by': 'example',
            }),
            content_type='application/json')

        assert res.status_code == 404

    def test_get_brief(self):
        NOW = pendulum.create(2015, 1, 1, 12, 34, 56, tz='Australia/Sydney')

        with pendulum.test(NOW):
            self.setup_dummy_briefs(1, title="I need a Developer")
            res = self.client.get('/briefs/1')

            assert res.status_code == 200
            expected_data = COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy()
            expected_data.update(
                {
                    'id': 1,
                    'status': 'draft',
                    'frameworkSlug': 'digital-outcomes-and-specialists',
                    'frameworkFramework': 'dos',
                    'frameworkName': 'Digital Outcomes and Specialists',
                    'frameworkStatus': 'live',
                    'lot': 'digital-specialists',
                    'lotSlug': 'digital-specialists',
                    'lotName': 'Digital specialists',
                    'createdAt': mock.ANY,
                    'updatedAt': mock.ANY,
                    'links': {
                        'framework': 'http://localhost/frameworks/digital-outcomes-and-specialists',
                        'self': 'http://localhost/briefs/1',
                    },
                    'users': [
                        {
                            'id': 1,
                            'emailAddress': 'test+1@digital.gov.au',
                            'phoneNumber': None,
                            'name': 'my name',
                            'role': 'buyer',
                            'active': True,
                        }
                    ],
                    "clarificationQuestions": [],
                    "dates": {
                        'answers_close': None,
                        'application_open_weeks': u'2 weeks',
                        'closing_date': None,
                        'closing_time': None,
                        'published_date': None,
                        'questions_close': None,
                        'questions_closing_date': None,
                        'hypothetical': {
                            'answers_close': '2015-01-14T07:00:00+00:00',
                            'application_open_weeks': u'2 weeks',
                            'closing_date': '2015-01-15',
                            'closing_time': '2015-01-15T07:00:00+00:00',
                            'published_date': '2015-01-01',
                            'questions_close': '2015-01-08T07:00:00+00:00',
                            'questions_closing_date': '2015-01-08'
                        }
                    },
                    "author": "my name",
                    "responsesZipFilesize": None
                }
            )

        loaded = json.loads(res.get_data(as_text=True))
        assert loaded == {"briefs": expected_data}

    def test_get_live_brief_has_published_at_time(self):
        NOW = pendulum.create(2015, 1, 1, 12, 34, 56, tz='Australia/Sydney')

        with pendulum.test(NOW):
            self.setup_dummy_briefs(1, status='live')
            res = self.client.get('/briefs/1')
            data = json.loads(res.get_data(as_text=True))

            assert 'publishedAt' in data['briefs']
            assert 'applicationsClosedAt' in data['briefs']
            assert 'clarificationQuestionsClosedAt' in data['briefs']
            assert 'clarificationQuestionsPublishedBy' in data['briefs']
            assert not data['briefs']['clarificationQuestionsAreClosed']

            assert data['briefs']['dates'] == {
                'answers_close': '2015-01-14T07:00:00+00:00',
                'application_open_weeks': u'2 weeks',
                'closing_date': '2015-01-15',
                'closing_time': '2015-01-15T07:00:00+00:00',
                'published_date': '2015-01-01',
                'questions_close': '2015-01-08T07:00:00+00:00',
                'questions_closing_date': '2015-01-08'
            }

    def test_get_brief_returns_404_if_not_found(self):
        res = self.client.get('/briefs/1')

        assert res.status_code == 404

    def test_list_briefs(self):
        self.setup_dummy_briefs(3)

        res = self.client.get('/briefs')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == data['meta']['total'] == 3

    def test_listed_briefs_do_not_list_users(self):
        self.setup_dummy_briefs(3)

        res = self.client.get('/briefs')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert not any('users' in brief for brief in data['briefs'])

    def test_list_briefs_by_user(self):
        self.setup_dummy_briefs(3, user_id=1)
        self.setup_dummy_briefs(2, user_id=2, brief_start=4)

        res = self.client.get('/briefs?user_id=1')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == 3

    def test_list_briefs_by_status(self):
        self.setup_dummy_briefs(3, status='live')
        self.setup_dummy_briefs(2, status='draft', brief_start=4)

        res = self.client.get('/briefs?status=live')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == data['meta']['total'] == 3, data['briefs']

    def test_cannot_list_briefs_by_invalid_status(self):
        self.setup_dummy_briefs(1, status='live')
        self.setup_dummy_briefs(1, status='draft', brief_start=2)

        res = self.client.get('/briefs?status=invalid')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == data['meta']['total'] == 0

    def test_list_briefs_by_multiple_statuses(self):
        self.setup_dummy_briefs(3, status='live')
        self.setup_dummy_briefs(2, status='draft', brief_start=4)

        res = self.client.get('/briefs?status=draft,live')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == data['meta']['total'] == 5, data['briefs']

    def test_list_briefs_by_framework(self):
        self.setup_dummy_briefs(3, status='live')
        self.setup_dummy_briefs(2, status='draft', brief_start=4)

        res = self.client.get('/briefs?framework=digital-outcomes-and-specialists')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == data['meta']['total'] == 5, data['briefs']

    def test_list_briefs_by_multiple_frameworks(self):
        self.setup_dummy_briefs(1, status='draft')
        self.setup_dummy_briefs(3, status='live', brief_start=2)

        # we don't have multiple brief-capable frameworks in the test dataset yet so this test is a bit of a stub
        # until we do. at least it tests framework slugs are properly split
        res = self.client.get('/briefs?framework=digital-outcomes-and-specialists,analogue-outcomes-and-specialists')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == data['meta']['total'] == 4, data['briefs']

    def test_cannot_list_briefs_by_invalid_framework(self):
        self.setup_dummy_briefs(1, status='live')
        self.setup_dummy_briefs(1, status='draft', brief_start=2)

        res = self.client.get('/briefs?framework=digital-biscuits-and-cakes')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == data['meta']['total'] == 0

    def test_list_briefs_by_framework_and_status(self):
        self.setup_dummy_briefs(3, status='live')
        self.setup_dummy_briefs(2, status='draft', brief_start=4)

        res = self.client.get('/briefs?framework=digital-outcomes-and-specialists&status=draft')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == data['meta']['total'] == 2, data['briefs']

    def test_list_briefs_by_lot(self):
        self.setup_dummy_briefs(3, status='live', lot='digital-outcomes')
        self.setup_dummy_briefs(1, status='draft', lot='digital-outcomes', brief_start=4)
        self.setup_dummy_briefs(2, status='live', lot='digital-specialists', brief_start=5)

        res = self.client.get('/briefs?lot=digital-outcomes')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == data['meta']['total'] == 4, data['briefs']

    def test_list_briefs_by_multiple_lots(self):
        self.setup_dummy_briefs(2, status='live', lot='digital-outcomes')
        self.setup_dummy_briefs(2, status='draft', lot='digital-specialists', brief_start=3)
        self.setup_dummy_briefs(1, status='draft', lot='digital-outcomes', brief_start=5)
        self.setup_dummy_briefs(3, status='live', lot='user-research-participants', brief_start=6)

        res = self.client.get('/briefs?lot=digital-specialists,user-research-participants')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == data['meta']['total'] == 5, data['briefs']
        assert all(
            (brief["lotSlug"] in ("digital-specialists", "user-research-participants",)) for brief in data['briefs']
        )

        res2 = self.client.get('/briefs?lot=banana,digital-specialists,,user-research-participants,')
        data2 = json.loads(res.get_data(as_text=True))

        assert res2.status_code == 200
        assert data['briefs'] == data2['briefs']

    def test_list_briefs_by_lot_and_status(self):
        self.setup_dummy_briefs(3, status='live', lot='digital-outcomes')
        self.setup_dummy_briefs(1, status='draft', lot='digital-outcomes', brief_start=4)
        self.setup_dummy_briefs(2, status='live', lot='digital-specialists', brief_start=5)

        res = self.client.get('/briefs?lot=digital-outcomes&status=live')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == data['meta']['total'] == 3, data['briefs']

    def test_list_briefs_by_human_readable(self):
        today = pendulum.utcnow()
        self.setup_dummy_briefs(1, data={'requirementsLength': '2 weeks'}, status=None, title='First',
                                published_at=(today + timedelta(days=-40)))
        self.setup_dummy_briefs(1, data={'requirementsLength': '2 weeks'}, status=None, title='Second',
                                published_at=(today + timedelta(days=-9)), brief_start=2)
        self.setup_dummy_briefs(1, data={'requirementsLength': '1 week'}, status=None, title='Third',
                                published_at=(today + timedelta(days=-8)), brief_start=3)
        self.setup_dummy_briefs(1, data={'requirementsLength': '1 week'}, status=None, title='Fourth',
                                published_at=(today + timedelta(days=-2)), brief_start=4)

        res = self.client.get('/briefs?human=True')
        data = json.loads(res.get_data(as_text=True))
        titles = list(map(lambda brief: brief['title'], data['briefs']))

        assert res.status_code == 200
        assert titles == ['Fourth', 'Third', 'Second', 'First']

    def test_list_briefs_pagination_page_one(self):
        self.setup_dummy_briefs(7)

        res = self.client.get('/briefs')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        assert len(data['briefs']) == 5
        assert data['meta']['total'] == 7
        assert data['links']['next'] == 'http://localhost/briefs?page=2'
        assert data['links']['last'] == 'http://localhost/briefs?page=2'

    def test_list_briefs_pagination_page_two(self):
        self.setup_dummy_briefs(7)

        res = self.client.get('/briefs?page=2')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        assert len(data['briefs']) == 2
        assert data['meta']['total'] == 7
        assert data['links']['prev'] == 'http://localhost/briefs?page=1'

    def test_list_briefs_no_pagination_if_user_id_supplied(self):
        self.setup_dummy_briefs(7)

        res = self.client.get('/briefs?user_id=1')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        assert len(data['briefs']) == 7
        assert data['links'] == {}

    def test_results_per_page(self):
        self.setup_dummy_briefs(7)
        response = self.client.get('/briefs?per_page=2')
        assert response.status_code == 200
        data = json.loads(response.get_data(as_text=True))
        assert 'briefs' in data
        assert len(data['briefs']) == 2

    def test_invalid_results_per_page(self):
        response = self.client.get('/briefs?per_page=bork')
        assert response.status_code == 400
        assert 'per_page' in response.get_data(as_text=True)

    def test_make_a_brief_live(self):
        self.setup_dummy_briefs(1, title='The Title')

        res = self.client.put(
            '/briefs/1/status',
            data=json.dumps({
                'briefs': {'status': 'live'},
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['briefs']['status'] == 'live'

    def test_cannot_make_a_brief_live_if_is_not_complete(self):
        self.setup_dummy_briefs(1)

        res = self.client.put(
            '/briefs/1/status',
            data=json.dumps({
                'briefs': {'status': 'live'},
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == {'title': 'answer_required'}

    def test_published_at_is_not_updated_if_live_brief_is_made_live(self):
        self.setup_dummy_briefs(1, status='live', title='The title')

        res = self.client.get('/briefs/1')
        original_published_at = json.loads(res.get_data(as_text=True))['briefs']['publishedAt']

        res = self.client.put(
            '/briefs/1/status',
            data=json.dumps({
                'briefs': {'status': 'live'},
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        res = self.client.get('/briefs/1')
        published_at = json.loads(res.get_data(as_text=True))['briefs']['publishedAt']
        assert published_at == original_published_at

    def test_cannot_make_a_brief_live_if_the_framework_is_no_longer_live(self):
        self.setup_dummy_briefs(1, title='The title')

        with self.app.app_context():
            framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
            framework.status = 'expired'
            db.session.add(framework)
            db.session.commit()

        res = self.client.put(
            '/briefs/1/status',
            data=json.dumps({
                'briefs': {'status': 'live'},
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == "Framework is not live"

    def test_cannot_set_status_to_invalid_value(self):
        self.setup_dummy_briefs(1, status='draft')

        res = self.client.put(
            '/briefs/1/status',
            data=json.dumps({
                'briefs': {'status': 'invalid'},
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == "Cannot change brief status from 'draft' to 'invalid'"

    def test_change_status_makes_audit_event(self):
        self.setup_dummy_briefs(1, title='The Title')

        res = self.client.put(
            '/briefs/1/status',
            data=json.dumps({
                'briefs': {'status': 'live'},
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        assert res.status_code == 200

        audit_response = self.client.get('/audit-events')
        assert audit_response.status_code == 200
        data = json.loads(audit_response.get_data(as_text=True))

        brief_audits = [event for event in data['auditEvents'] if event['type'] == AuditTypes.update_brief_status.value]
        assert len(brief_audits) == 1
        assert brief_audits[0]['data'] == {
            'briefId': mock.ANY,
            'briefStatus': 'live',
        }

    @mock.patch('app.tasks.publish_tasks.brief')
    def test_publish_a_brief(self, brief):
        self.setup_dummy_briefs(1, title='The Title')

        res = self.client.post(
            '/briefs/1/publish',
            data=json.dumps({
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['briefs']['status'] == 'live'
        assert brief.delay.called is True

    @mock.patch('app.tasks.publish_tasks.brief')
    def test_withdraw_a_brief(self, brief):
        self.setup_dummy_briefs(1, title='The Title', status='live')

        res = self.client.post(
            '/briefs/1/withdraw',
            data=json.dumps({
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['briefs']['status'] == 'withdrawn'
        assert data['briefs']['withdrawnAt'] is not None
        assert brief.delay.called is True

    def test_cannot_publish_withdrawn_brief(self):
        self.setup_dummy_briefs(1, title='The Title', status='withdrawn')

        res = self.client.post(
            '/briefs/1/publish',
            data=json.dumps({
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        json.loads(res.get_data(as_text=True))

        assert res.status_code == 400

    def test_cannot_publish_a_brief_if_is_not_complete(self):
        self.setup_dummy_briefs(1)

        res = self.client.post(
            '/briefs/1/publish',
            data=json.dumps({
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == {'title': 'answer_required'}

    def test_published_at_is_not_updated_if_live_brief_is_published(self):
        self.setup_dummy_briefs(1, status='live', title='The title')

        res = self.client.get('/briefs/1')
        original_published_at = json.loads(res.get_data(as_text=True))['briefs']['publishedAt']

        res = self.client.post(
            '/briefs/1/publish',
            data=json.dumps({
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')

        assert res.status_code == 200

        res = self.client.get('/briefs/1')
        published_at = json.loads(res.get_data(as_text=True))['briefs']['publishedAt']
        assert published_at == original_published_at

    def test_withdrawn_at_is_not_updated_if_withdrawn_brief_is_withdrawn(self):
        self.setup_dummy_briefs(1, title='The title', status='withdrawn')

        res = self.client.get('/briefs/1')
        original_withdrawn_at = json.loads(res.get_data(as_text=True))['briefs']['withdrawnAt']

        res = self.client.post(
            '/briefs/1/withdraw',
            data=json.dumps({
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        res = self.client.get('/briefs/1')
        withdrawn_at = json.loads(res.get_data(as_text=True))['briefs']['withdrawnAt']
        assert withdrawn_at == original_withdrawn_at

    def test_cannot_publish_a_brief_if_the_framework_is_no_longer_live(self):
        self.setup_dummy_briefs(1, title='The title')

        with self.app.app_context():
            framework = Framework.query.filter(Framework.slug == "digital-outcomes-and-specialists").first()
            framework.status = 'expired'
            db.session.add(framework)
            db.session.commit()

        res = self.client.post(
            '/briefs/1/publish',
            data=json.dumps({
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == "Framework is not live"

    @mock.patch('app.tasks.publish_tasks.brief')
    def test_publish_brief_makes_audit_event(self, brief):
        self.setup_dummy_briefs(1, title='The Title')

        res = self.client.post(
            '/briefs/1/publish',
            data=json.dumps({
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        assert res.status_code == 200
        assert brief.delay.called is True

        audit_response = self.client.get('/audit-events')
        assert audit_response.status_code == 200
        data = json.loads(audit_response.get_data(as_text=True))

        brief_audits = [event for event in data['auditEvents'] if event['type'] == AuditTypes.update_brief_status.value]
        assert len(brief_audits) == 1
        assert brief_audits[0]['data'] == {
            'briefId': mock.ANY,
            'briefPreviousStatus': 'draft',
            'briefStatus': 'live',
        }

    @mock.patch('app.tasks.publish_tasks.brief')
    def test_withdraw_brief_makes_audit_event(self, brief):
        self.setup_dummy_briefs(1, title='The Title', status='live')

        res = self.client.post(
            '/briefs/1/withdraw',
            data=json.dumps({
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        assert res.status_code == 200
        assert brief.delay.called is True

        audit_response = self.client.get('/audit-events')
        assert audit_response.status_code == 200
        data = json.loads(audit_response.get_data(as_text=True))

        brief_audits = [event for event in data['auditEvents'] if event['type'] == AuditTypes.update_brief_status.value]
        assert len(brief_audits) == 1
        assert brief_audits[0]['data'] == {
            'briefId': mock.ANY,
            'briefPreviousStatus': 'live',
            'briefStatus': 'withdrawn',
        }

    def test_can_delete_a_draft_brief(self):
        res = self.client.post(
            '/briefs',
            data=json.dumps({
                'briefs': {
                    'userId': self.user_id,
                    'frameworkSlug': 'digital-outcomes-and-specialists',
                    'lot': 'digital-specialists',
                    'title': 'the title',
                },
                'updated_by': 'example'
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 201
        brief_id = data['briefs']['id']

        fetch = self.client.get('/briefs/{}'.format(brief_id))
        assert fetch.status_code == 200

        delete = self.client.delete(
            '/briefs/{}'.format(brief_id),
            data=json.dumps({'update_details': {'updated_by': 'deleter'}}),
            content_type='application/json')
        assert delete.status_code == 200

        audit_response = self.client.get('/audit-events')
        assert audit_response.status_code == 200
        audit_data = json.loads(audit_response.get_data(as_text=True))
        assert len(audit_data['auditEvents']) == 2
        assert audit_data['auditEvents'][0]['type'] == 'create_brief'
        assert audit_data['auditEvents'][1]['type'] == 'delete_brief'
        assert audit_data['auditEvents'][1]['user'] == 'deleter'
        assert audit_data['auditEvents'][1]['data']['briefId'] == brief_id

        fetch_again = self.client.get('/briefs/{}'.format(brief_id))
        assert fetch_again.status_code == 404

    def test_can_not_delete_a_live_brief(self):
        self.setup_dummy_briefs(1, status='live')

        delete = self.client.delete(
            '/briefs/1',
            data=json.dumps({'update_details': {'updated_by': 'deleter'}}),
            content_type='application/json')
        assert delete.status_code == 400

        error = json.loads(delete.get_data(as_text=True))['error']
        assert error == u"Cannot delete a live brief"

        fetch_again = self.client.get('/briefs/1')
        assert fetch_again.status_code == 200

    def test_can_not_delete_a_closed_brief(self):
        self.setup_dummy_briefs(1, status='closed')

        delete = self.client.delete(
            '/briefs/1',
            data=json.dumps({'update_details': {'updated_by': 'deleter'}}),
            content_type='application/json')
        assert delete.status_code == 400

        error = json.loads(delete.get_data(as_text=True))['error']
        assert error == u"Cannot delete a closed brief"

        fetch_again = self.client.get('/briefs/1')
        assert fetch_again.status_code == 200

    def test_reject_delete_with_no_updated_by(self):
        res = self.client.delete('/briefs/0000000000',
                                 data=json.dumps({}),
                                 content_type='application/json')
        assert res.status_code == 400
        error = json.loads(res.get_data(as_text=True))['error']
        assert "'updated_by' is a required property" in error

    def test_should_404_on_delete_a_brief_that_doesnt_exist(self):
        res = self.client.delete(
            '/briefs/0000000000',
            data=json.dumps({'updated_by': 'example'}),
            content_type='application/json'
        )
        assert res.status_code == 404

    def test_add_clarification_question(self):
        self.setup_dummy_briefs(1, title="The Title", status="live")

        res = self.client.post(
            "/briefs/1/clarification-questions",
            data=json.dumps({
                "clarificationQuestion": {
                    "question": "What?",
                    "answer": "That",
                },
                "update_details": {"updated_by": "example"},
            }),
            content_type="application/json")
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data["briefs"]["clarificationQuestions"] == [{
            "question": "What?",
            "answer": "That",
            "publishedAt": mock.ANY,
        }]

    def test_clarification_question_strip_whitespace(self):
        self.setup_dummy_briefs(1, title="The Title", status="live")

        res = self.client.post(
            "/briefs/1/clarification-questions",
            data=json.dumps({
                "clarificationQuestion": {
                    "question": "What? ",
                    "answer": "That ",
                },
                "update_details": {"updated_by": "example"},
            }),
            content_type="application/json")
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data["briefs"]["clarificationQuestions"] == [{
            "question": "What?",
            "answer": "That",
            "publishedAt": mock.ANY,
        }]

    def test_add_clarification_question_fails_if_no_question(self):
        self.setup_dummy_briefs(1, title="The Title", status="live")

        res = self.client.post(
            "/briefs/1/clarification-questions",
            data=json.dumps({
                "clarificationQuestion": {
                    "answer": "That",
                },
                "updated_by": "example",
            }),
            content_type="application/json")

        assert res.status_code == 400

    def test_add_clarification_question_fails_if_no_answer(self):
        self.setup_dummy_briefs(1, title="The Title", status="live")

        res = self.client.post(
            "/briefs/1/clarification-questions",
            data=json.dumps({
                "clarificationQuestion": {
                    "question": "What?",
                },
                "update_details": {"updated_by": "example"},
            }),
            content_type="application/json")

        assert res.status_code == 400

    def test_cannot_get_clarification_questions_directly(self):
        self.setup_dummy_briefs(1, title="The Title", status="live")

        res = self.client.get("/briefs/1/clarification-questions")

        assert res.status_code == 405

    def test_adding_a_clarification_question_makes_an_audit_event(self):
        self.setup_dummy_briefs(1, title="The Title", status="live")

        self.client.post(
            "/briefs/1/clarification-questions",
            data=json.dumps({
                "clarificationQuestion": {
                    "question": "What?",
                    "answer": "That",
                },
                "updated_by": "example",
            }),
            content_type="application/json")

        audit_response = self.client.get("/audit-events")
        assert audit_response.status_code == 200
        data = json.loads(audit_response.get_data(as_text=True))

        audits = [
            event for event in data["auditEvents"]
            if event["type"] == AuditTypes.add_brief_clarification_question.value
        ]

        assert len(audits) == 1
        assert audits[0]['data'] == {
            "question": "What?",
            "answer": "That",
        }

    def test_cannot_make_a_draft_copy_of_a_brief_if_the_framework_is_closed(self):
        self.setup_dummy_briefs(1, title="The Title", status="withdrawn")

        with self.app.app_context():
            framework = Framework.query.filter(Framework.slug == "digital-outcomes-and-specialists").first()
            framework.status = 'expired'
            db.session.add(framework)
            db.session.commit()

        res = self.client.post(
            "/briefs/1/copy",
            data=json.dumps({'updated_by': 'example'}),
            content_type="application/json")
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == "Framework is not live"

    def test_make_a_draft_copy_of_a_brief(self):
        # Set up brief with clarification question
        self.setup_dummy_briefs(1, title="The Title", status="live")
        with self.app.app_context():
            brief = Brief.query.get(1)
            brief.add_clarification_question('question', 'answer')
            db.session.add(brief)
            db.session.commit()

        res = self.client.post(
            "/briefs/1/copy",
            data=json.dumps({'updated_by': 'example'}),
            content_type="application/json")
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 201
        assert data["briefs"]["id"] > 1
        assert data["briefs"]["lot"] == 'digital-specialists'
        assert data["briefs"]["frameworkSlug"] == 'digital-outcomes-and-specialists'
        assert data["briefs"]["status"] == 'draft'
        assert data["briefs"]["title"] == 'The Title'
        assert not data["briefs"]["clarificationQuestions"]

    def test_make_a_draft_copy_of_a_brief_makes_audit_event(self):
        self.setup_dummy_briefs(1, title="The Title", status="withdrawn")

        res = self.client.post(
            "/briefs/1/copy",
            data=json.dumps({'updated_by': 'example'}),
            content_type="application/json")
        assert res.status_code == 201

        audit_response = self.client.get('/audit-events')
        assert audit_response.status_code == 200
        data = json.loads(audit_response.get_data(as_text=True))

        brief_audits = [event for event in data['auditEvents'] if event['type'] == AuditTypes.create_brief.value]
        assert len(brief_audits) == 1
        assert brief_audits[0]['data']['originalBriefId'] == 1
        assert brief_audits[0]['data']['briefId'] > 1


class TestSupplierIsEligibleForBrief(BaseApplicationTest):
    def setup_services(self):
        with self.app.app_context():
            self.setup_dummy_suppliers(2)
            self.set_framework_status("digital-outcomes-and-specialists", "live")
            framework = Framework.query.filter(Framework.slug == "digital-outcomes-and-specialists").first()

            self.setup_dummy_service(
                service_id='10000000001',
                supplier_code=0,
                framework_id=framework.id,  # Digital Outcomes and Specialists
                lot_id=framework.get_lot('digital-outcomes').id,  # digital-outcomes
                data={"locations": [
                    "London", "Offsite", "Scotland", "Wales"
                ]
                })
            self.setup_dummy_service(
                service_id='10000000002',
                supplier_code=0,
                framework_id=framework.id,  # Digital Outcomes and Specialists
                lot_id=framework.get_lot('digital-specialists').id,  # digital-specialists
                data={"developerLocations": ["London", "Offsite", "Scotland", "Wales"]}
            )
            self.setup_dummy_service(
                service_id='10000000003',
                supplier_code=1,
                framework_id=framework.id,  # Digital Outcomes and Specialists
                lot_id=framework.get_lot('digital-specialists').id,  # digital-specialists
                data={"developerLocations": ["Wales"]}
            )
            db.session.commit()

    def test_supplier_is_eligible_for_specialist(self):
        self.setup_services()
        self.setup_dummy_briefs(1, status="live")

        response = self.client.get("/briefs/1/services?supplier_code=0")
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200, response.get_data(as_text=True)
        assert len(data["services"]) == 1

    def test_supplier_is_eligible_for_outcome(self):
        self.setup_services()
        with self.app.app_context():
            self.setup_dummy_user(id=1)
            self.setup_dummy_brief(
                id=1,
                status="live",
                user_id=1,
                data={"location": "London"},
                lot_slug="digital-outcomes")
            db.session.commit()

        response = self.client.get("/briefs/1/services?supplier_code=0")
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        assert data["services"]

    def test_supplier_code_must_be_provided(self):
        self.setup_services()
        self.setup_dummy_briefs(1, status="live")

        response = self.client.get("/briefs/1/services")

        assert response.status_code == 404

    def test_supplier_is_ineligible_if_brief_not_live(self):
        self.setup_services()
        self.setup_dummy_briefs(1, status="draft")

        response = self.client.get("/briefs/1/services?supplier_code=0")

        assert response.status_code == 404

    def test_supplier_is_eligible_even_if_not_in_specialist_location(self):
        self.setup_services()
        with self.app.app_context():
            self.setup_dummy_user(id=1)
            self.setup_dummy_brief(
                id=1,
                status="live",
                user_id=1,
                data={"location": "North East England",
                      "specialistRole": "developer"})
            db.session.commit()

        response = self.client.get("/briefs/1/services?supplier_code=0")
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        assert data["services"]

    def test_supplier_is_ineligible_if_does_not_supply_the_role(self):
        self.setup_services()
        with self.app.app_context():
            self.setup_dummy_user(id=1)
            self.setup_dummy_brief(
                id=1,
                status="live",
                user_id=1,
                data={"location": "London",
                      "specialistRole": "agileCoach"})
            db.session.commit()

        response = self.client.get("/briefs/1/services?supplier_code=0")
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        assert not data["services"]

    def test_supplier_is_eligible_even_if_does_not_supply_in_outcome_location(self):
        self.setup_services()
        with self.app.app_context():
            self.setup_dummy_user(id=1)
            self.setup_dummy_brief(
                id=1,
                status="live",
                user_id=1,
                data={"location": "North East England"},
                lot_slug="digital-outcomes")
            db.session.commit()

        response = self.client.get("/briefs/1/services?supplier_code=0")
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        assert data["services"]


class TestCounts(BaseApplicationTest):
    def test_get_briefs(self):
        response = self.client.get('/briefs/count')
        assert response.status_code == 200
