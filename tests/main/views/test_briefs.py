import json
from datetime import datetime
from datetime import timedelta

from freezegun import freeze_time
import pytest
import mock
from tests.helpers import COMPLETE_DIGITAL_SPECIALISTS_BRIEF, FixtureMixin, get_audit_events
from tests.bases import BaseApplicationTest

from dmapiclient.audit import AuditTypes
from app import db
from app.models import Framework, BriefResponse, Brief, Lot


class FrameworkSetupAndTeardown(BaseApplicationTest, FixtureMixin):
    def setup(self):
        super(FrameworkSetupAndTeardown, self).setup()
        self.user_id = self.setup_dummy_user(role='buyer')

        framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
        self._original_framework_status = framework.status
        framework.status = 'live'

        db.session.add(framework)
        db.session.commit()

    def teardown(self):
        framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
        framework.status = self._original_framework_status

        db.session.add(framework)
        db.session.commit()
        super(FrameworkSetupAndTeardown, self).teardown()


class TestCreateBrief(FrameworkSetupAndTeardown):
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

        assert res.status_code == 201
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

    def test_create_brief_fails_if_framework_not_live(self):
        for framework_status in [status for status in Framework.STATUSES if status != 'live']:
            framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
            self._original_framework_status = framework.status
            framework.status = framework_status

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


class TestUpdateBrief(FrameworkSetupAndTeardown):
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
                'briefs': {'technicalWeighting': 15, 'culturalWeighting': 75, 'priceWeighting': 10},
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


class TestGetBrief(FrameworkSetupAndTeardown):
    def test_get_brief(self):
        self.setup_dummy_briefs(1, title="I need a Developer")
        res = self.client.get('/briefs/1')

        assert res.status_code == 200
        expected_data = COMPLETE_DIGITAL_SPECIALISTS_BRIEF.copy()

        expected_data.update(
            {
                'id': 1,
                'status': 'draft',
                'frameworkSlug': 'digital-outcomes-and-specialists',
                'frameworkFramework': 'digital-outcomes-and-specialists',
                'frameworkName': 'Digital Outcomes and Specialists',
                'frameworkStatus': 'live',
                'framework': {
                    'family': 'digital-outcomes-and-specialists',
                    'name': 'Digital Outcomes and Specialists',
                    'slug': 'digital-outcomes-and-specialists',
                    'status': 'live',
                },
                'isACopy': False,
                'lot': 'digital-specialists',
                'lotSlug': 'digital-specialists',
                'lotName': 'Digital specialists',
                'createdAt': mock.ANY,
                'updatedAt': mock.ANY,
                'links': {
                    'framework': 'http://127.0.0.1:5000/frameworks/digital-outcomes-and-specialists',
                    'self': 'http://127.0.0.1:5000/briefs/1',
                },
                'users': [
                    {
                        'id': 1,
                        'emailAddress': 'test+1@digital.gov.uk',
                        'phoneNumber': None,
                        'name': 'my name',
                        'role': 'buyer',
                        'active': True,
                        'userResearchOptedIn': False,
                        'personalDataRemoved': False,
                    }
                ],
                "clarificationQuestions": [],
            }
        )

        assert json.loads(res.get_data(as_text=True)) == {"briefs": expected_data}

    def test_get_live_brief_has_published_at_time(self):
        self.setup_dummy_briefs(1, status='live')
        res = self.client.get('/briefs/1')
        data = json.loads(res.get_data(as_text=True))

        assert 'publishedAt' in data['briefs']
        assert 'applicationsClosedAt' in data['briefs']
        assert 'clarificationQuestionsClosedAt' in data['briefs']
        assert 'clarificationQuestionsPublishedBy' in data['briefs']
        assert not data['briefs']['clarificationQuestionsAreClosed']

    def test_get_brief_returns_404_if_not_found(self):
        res = self.client.get('/briefs/1')

        assert res.status_code == 404


class TestListBrief(FrameworkSetupAndTeardown):
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
        today = datetime.utcnow()
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
        assert titles == ['Fourth', 'Second', 'Third', 'First']

    @pytest.mark.parametrize("with_users", ["true", "True"])
    def test_list_briefs_with_user_data_set_true(self, with_users):
        self.setup_dummy_briefs(1, title="Test Brief", user_id=123)

        response = self.client.get('/briefs?with_users=' + with_users)
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        assert data['briefs'][0]['users'][0]['name'] == 'my name'

    def test_list_briefs_with_user_data_set_false(self):
        self.setup_dummy_briefs(1, title="Test Brief", user_id=123)

        response = self.client.get('/briefs?with_users=false')
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        with pytest.raises(KeyError):
            data['briefs'][0]['users']

    @pytest.mark.parametrize("user_id", ["&user_id=123", ""])
    @pytest.mark.parametrize("with_clarification_questions", ["true", "True"])
    def test_list_briefs_with_clarification_questions_data_set_true(self, with_clarification_questions, user_id):
        # We test with both filtering by user_id and not because this will trigger both paginated and unpaginated
        # responses
        self.setup_dummy_briefs(1, title="Test Brief", user_id=123, add_clarification_question=True, status='live')

        response = self.client.get('/briefs?with_clarification_questions=' + with_clarification_questions + user_id)
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        assert data['briefs'][0]['clarificationQuestions'][0]['answer'] == '42'

    @pytest.mark.parametrize("user_id", ["?user_id=123", ""])
    def test_list_briefs_does_not_include_clarification_questions_by_default(self, user_id):
        # We test with both filtering by user_id and not because this will trigger both paginated and unpaginated
        # responses
        self.setup_dummy_briefs(1, title="Test Brief", user_id=123, add_clarification_question=True, status='live')

        response = self.client.get('/briefs' + user_id)
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        assert "clarificationQuestions" not in data['briefs'][0]

    def test_list_briefs_pagination_page_one(self):
        self.setup_dummy_briefs(7)

        res = self.client.get('/briefs')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        assert len(data['briefs']) == 5
        assert data['meta']['total'] == 7
        assert data['links']['next'] == 'http://127.0.0.1:5000/briefs?page=2'
        assert data['links']['last'] == 'http://127.0.0.1:5000/briefs?page=2'

    def test_list_briefs_pagination_page_two(self):
        self.setup_dummy_briefs(7)

        res = self.client.get('/briefs?page=2')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        assert len(data['briefs']) == 2
        assert data['meta']['total'] == 7
        assert data['links']['prev'] == 'http://127.0.0.1:5000/briefs?page=1'

    def test_list_briefs_no_pagination_if_user_id_supplied(self):
        self.setup_dummy_briefs(7)

        res = self.client.get('/briefs?user_id=1')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        assert len(data['briefs']) == 7

    @pytest.mark.parametrize('date_arg', ['published_on', 'withdrawn_on', 'cancelled_on', 'unsuccessful_on'])
    def test_list_briefs_filter_by_single_day(self, date_arg):
        for i, brief_status in enumerate(["draft", "withdrawn", "live", "cancelled", "unsuccessful"]):
            with freeze_time('2017-01-01 00:00:00'):
                self.setup_dummy_briefs(1, lot='digital-outcomes', status=brief_status, brief_start=i + 1)
            with freeze_time('2017-01-01 23:59:59.999999'):
                self.setup_dummy_briefs(1, lot='digital-outcomes', status=brief_status, brief_start=i + 6)

            # The following briefs should be outside the time span
            with freeze_time('2016-12-31 23:59:59.999999'):
                self.setup_dummy_briefs(1, lot='digital-outcomes', status=brief_status, brief_start=i + 11)
            with freeze_time('2017-01-02 00:00:00'):
                self.setup_dummy_briefs(1, lot='digital-outcomes', status=brief_status, brief_start=i + 16)

        res = self.client.get('/briefs?{}=2017-01-01'.format(date_arg))
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == 2

    @pytest.mark.parametrize(
        'date_arg,expected_count',
        [('published_before', 5), ('withdrawn_before', 1), ('cancelled_before', 1), ('unsuccessful_before', 1)]
    )
    def test_list_briefs_filter_before_date(self, date_arg, expected_count):
        for i, brief_status in enumerate(["draft", "withdrawn", "live", "cancelled", "unsuccessful"]):
            with freeze_time('2016-12-31 23:59:59.999999'):
                self.setup_dummy_briefs(1, lot='digital-outcomes', status=brief_status, brief_start=i + 1)
            # The following briefs should be filtered out ('before' is not inclusive)
            with freeze_time('2017-01-01 00:00:00'):
                self.setup_dummy_briefs(1, lot='digital-outcomes', status=brief_status, brief_start=i + 6)

        res = self.client.get('/briefs?{}=2017-01-01'.format(date_arg))
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        # When setting statuses on our dummy Briefs, we also set an 'old' published_at date,
        #  so there will be more results for the `published_before` query than the others.
        assert len(data['briefs']) == expected_count

    @pytest.mark.parametrize(
        'date_arg', ['published_after', 'withdrawn_after', 'cancelled_after', 'unsuccessful_after']
    )
    def test_list_briefs_filter_after_date(self, date_arg):
        for i, brief_status in enumerate(["draft", "withdrawn", "live", "cancelled", "unsuccessful"]):
            with freeze_time('2017-01-02 00:00:00'):
                self.setup_dummy_briefs(1, lot='digital-outcomes', status=brief_status, brief_start=i + 1)
            # The following briefs should be filtered out ('after' is not inclusive)
            with freeze_time('2017-01-01 23:59:59.999999'):
                self.setup_dummy_briefs(1, lot='digital-outcomes', status=brief_status, brief_start=i + 6)

        res = self.client.get('/briefs?{}=2017-01-01'.format(date_arg))
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == 1

    @pytest.mark.parametrize('temporal_arg, expected_count', [('before', 1), ('on', 2), ('after', 1)])
    def test_list_briefs_filter_closed_briefs_by_date(self, temporal_arg, expected_count):
        # Closed briefs need to be set up differently, so this test covers all 3 before/after/on cases
        framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
        lot = Lot.query.filter(Lot.slug == 'digital-specialists').first()

        with freeze_time('2017-01-01 23:59:59.999999'):
            brief1 = Brief(data={}, framework=framework, lot=lot, published_at=datetime.utcnow())
        with freeze_time('2017-01-02 00:00:00'):
            brief2 = Brief(data={}, framework=framework, lot=lot, published_at=datetime.utcnow())
        with freeze_time('2017-01-02 23:59:59.999999'):
            brief3 = Brief(data={}, framework=framework, lot=lot, published_at=datetime.utcnow())
        with freeze_time('2017-01-03 00:00:00'):
            brief4 = Brief(data={}, framework=framework, lot=lot, published_at=datetime.utcnow())

        db.session.add_all([brief1, brief2, brief3, brief4])
        db.session.commit()

        res = self.client.get('/briefs?closed_{}=2017-01-16'.format(temporal_arg))
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == expected_count

    @pytest.mark.parametrize("querystr,expect_compression", (
        ("status=live", True),
        ("status=live,unsuccessful,awarded&with_clarification_questions=true", True),
        ("status=live,withdrawn", False),
        ("status=live&with_users=true", False),
        ("status=draft", False),
        ("", False),
    ))
    def test_compress_when_appropriate(self, querystr, expect_compression):
        self.setup_dummy_briefs(10, status='live', title="U. P. up " * 50, add_clarification_question=True)
        self.setup_dummy_briefs(2, status='unsuccessful', brief_start=20)
        self.setup_dummy_briefs(2, status='draft', data={"jink": "a jink " * 600}, brief_start=30)

        res = self.client.get(f'/briefs?{querystr}', headers={"Accept-Encoding": "gzip"})
        assert (res.headers.get("Content-Encoding") == "gzip") is expect_compression
        if not expect_compression:
            # otherwise it's not been a useful test because it just didn't reach the minimum compressable size
            assert len(res.get_data()) > 8000


@mock.patch('app.main.views.briefs.index_brief', autospec=True)
class TestUpdateBriefStatus(FrameworkSetupAndTeardown):
    def test_publish_a_brief(self, index_brief):
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
        assert index_brief.called is True

    @pytest.mark.parametrize(('framework_status'), ('live', 'expired'))
    def test_withdraw_a_brief(self, index_brief, framework_status):
        framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
        framework.status = framework_status
        db.session.add(framework)
        db.session.commit()

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
        assert index_brief.called is True

    @pytest.mark.parametrize('framework_status', ('pending', 'expired'))
    def test_cancel_a_brief(self, index_brief, framework_status):
        self.setup_dummy_briefs(1, title='The Title', status='closed')
        framework = Framework.query.filter(Framework.slug == 'digital-outcomes-and-specialists').first()
        framework.status = framework_status
        db.session.add(framework)
        db.session.commit()

        res = self.client.post(
            '/briefs/1/cancel',
            data=json.dumps({
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['briefs']['status'] == 'cancelled'
        assert index_brief.called is True

    def test_update_a_brief_as_unsuccessful(self, index_brief):
        self.setup_dummy_briefs(1, title='The Title', status='closed')

        res = self.client.post(
            '/briefs/1/unsuccessful',
            data=json.dumps({
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['briefs']['status'] == 'unsuccessful'
        assert index_brief.called is True

    def test_cannot_publish_withdrawn_brief(self, index_brief):
        self.setup_dummy_briefs(1, title='The Title', status='withdrawn')

        res = self.client.post(
            '/briefs/1/publish',
            data=json.dumps({
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')

        assert res.status_code == 400
        assert index_brief.called is False

    def test_cannot_publish_a_brief_if_is_not_complete(self, index_brief):
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
        assert index_brief.called is False

    def test_published_at_is_not_updated_if_live_brief_is_published(self, index_brief):
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
        assert index_brief.called is False

    def test_withdrawn_at_is_not_updated_if_withdrawn_brief_is_withdrawn(self, index_brief):
        self.setup_dummy_briefs(1, title='The title', status='withdrawn')

        res = self.client.get('/briefs/1')
        original_withdrawn_at = json.loads(res.get_data(as_text=True))['briefs']['withdrawnAt']

        res = self.client.post(
            '/briefs/1/withdraw',
            data=json.dumps({
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')

        assert res.status_code == 200

        res = self.client.get('/briefs/1')
        withdrawn_at = json.loads(res.get_data(as_text=True))['briefs']['withdrawnAt']
        assert withdrawn_at == original_withdrawn_at
        assert index_brief.called is False

    def test_cannot_publish_a_brief_if_the_framework_is_not_live(self, index_brief):
        self.setup_dummy_briefs(1, title='The title')

        for framework_status in [status for status in Framework.STATUSES if status != 'live']:
            framework = Framework.query.get(5)
            framework.status = framework_status
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
            assert index_brief.called is False

    @pytest.mark.parametrize(
        ('old_status', 'url_arg', 'new_status'),
        (
            ('draft', 'publish', 'live'),
            ('live', 'withdraw', 'withdrawn'),
            ('closed', 'cancel', 'cancelled'),
            ('closed', 'unsuccessful', 'unsuccessful')
        )
    )
    def test_brief_status_change_makes_audit_event(self, index_brief, old_status, url_arg, new_status):
        self.setup_dummy_briefs(1, title='The Title', status=old_status)

        res = self.client.post(
            '/briefs/1/{}'.format(url_arg),
            data=json.dumps({
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        assert res.status_code == 200
        assert index_brief.called is True

        audit_response = self.client.get('/audit-events')
        assert audit_response.status_code == 200
        data = json.loads(audit_response.get_data(as_text=True))

        brief_audits = [event for event in data['auditEvents'] if event['type'] == AuditTypes.update_brief_status.value]
        assert len(brief_audits) == 1
        assert brief_audits[0]['data'] == {
            'briefId': mock.ANY,
            'briefPreviousStatus': old_status,
            'briefStatus': new_status,
        }


class TestDeleteBrief(FrameworkSetupAndTeardown):
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


class TestAddBriefClarificationQuestion(FrameworkSetupAndTeardown):
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


class TestCopyBrief(FrameworkSetupAndTeardown):
    def test_make_a_draft_copy_of_a_brief(self):
        self.setup_dummy_briefs(1, title="The Title", status="live")

        res = self.client.post(
            "/briefs/1/copy",
            data=json.dumps({'updated_by': 'example'}),
            content_type="application/json")
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 201
        assert data["briefs"]["id"] > 1

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


class TestSupplierIsEligibleForBrief(BaseApplicationTest, FixtureMixin):
    def setup_services(self):
        self.setup_dummy_suppliers(2)
        self.set_framework_status("digital-outcomes-and-specialists", "live")
        self.setup_dummy_service(
            service_id='10000000001',
            supplier_id=0,
            framework_id=5,  # Digital Outcomes and Specialists
            lot_id=5,  # digital-outcomes
            data={"locations": [
                "London", "Offsite", "Scotland", "Wales"
            ]
            })
        self.setup_dummy_service(
            service_id='10000000002',
            supplier_id=0,
            framework_id=5,  # Digital Outcomes and Specialists
            lot_id=6,  # digital-specialists
            data={"developerLocations": ["London", "Offsite", "Scotland", "Wales"]}
        )
        self.setup_dummy_service(
            service_id='10000000003',
            supplier_id=1,
            framework_id=5,  # Digital Outcomes and Specialists
            lot_id=6,  # digital-specialists
            data={"developerLocations": ["Wales"]}
        )

    def test_supplier_is_eligible_for_specialist(self):
        self.setup_services()
        self.setup_dummy_briefs(1, status="live")

        response = self.client.get("/briefs/1/services?supplier_id=0")
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        assert len(data["services"]) == 1

    def test_supplier_is_eligible_for_live_outcome(self):
        self.setup_services()
        self.setup_dummy_user(id=1)
        self.setup_dummy_brief(
            id=1,
            status="live",
            user_id=1,
            data={"location": "London"},
            lot_slug="digital-outcomes")
        db.session.commit()

        response = self.client.get("/briefs/1/services?supplier_id=0")
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        assert data["services"]

    def test_supplier_id_must_be_provided(self):
        self.setup_services()
        self.setup_dummy_briefs(1, status="live")

        response = self.client.get("/briefs/1/services")

        assert response.status_code == 404

    def test_supplier_is_ineligible_if_brief_in_draft(self):
        self.setup_services()
        self.setup_dummy_briefs(1, status="draft")

        response = self.client.get("/briefs/1/services?supplier_id=0")

        assert response.status_code == 404

    def test_supplier_is_eligible_if_brief_closed(self):
        self.setup_services()
        self.setup_dummy_briefs(1, status="closed")

        response = self.client.get("/briefs/1/services?supplier_id=0")
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        assert data["services"]

    def test_supplier_is_eligible_even_if_not_in_specialist_location(self):
        self.setup_services()
        self.setup_dummy_user(id=1)
        self.setup_dummy_brief(
            id=1,
            status="live",
            user_id=1,
            data={"location": "North East England",
                  "specialistRole": "developer"})
        db.session.commit()

        response = self.client.get("/briefs/1/services?supplier_id=0")
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        assert data["services"]

    def test_supplier_is_ineligible_if_does_not_supply_the_role(self):
        self.setup_services()
        self.setup_dummy_user(id=1)
        self.setup_dummy_brief(
            id=1,
            status="live",
            user_id=1,
            data={"location": "London",
                  "specialistRole": "agileCoach"})
        db.session.commit()

        response = self.client.get("/briefs/1/services?supplier_id=0")
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        assert not data["services"]

    def test_supplier_is_eligible_even_if_does_not_supply_in_outcome_location(self):
        self.setup_services()
        self.setup_dummy_user(id=1)
        self.setup_dummy_brief(
            id=1,
            status="live",
            user_id=1,
            data={"location": "North East England"},
            lot_slug="digital-outcomes")
        db.session.commit()

        response = self.client.get("/briefs/1/services?supplier_id=0")
        data = json.loads(response.get_data(as_text=True))

        assert response.status_code == 200
        assert data["services"]


class TestAwardPendingBriefResponse(FrameworkSetupAndTeardown):

    award_url = "/briefs/1/award"

    def _post_to_award_endpoint(self, payload):
        payload['update_details'] = {"updated_by": "example"}
        return self.client.post(
            self.award_url,
            data=json.dumps(payload),
            content_type="application/json"
        )

    def test_can_award_brief_response_to_closed_brief_without_award_details(self):
        self.setup_dummy_briefs(1, status="closed")
        self.setup_dummy_suppliers(1)
        brief_response = BriefResponse(brief_id=1, supplier_id=0, submitted_at=datetime.utcnow(), data={})
        db.session.add(brief_response)
        db.session.commit()
        brief_response_id = brief_response.id

        res = self._post_to_award_endpoint({'briefResponseId': brief_response.id})
        assert res.status_code == 200

        brief_response_audits = get_audit_events(self.client, AuditTypes.update_brief_response)
        assert len(brief_response_audits) == 1
        assert brief_response_audits[0]['data'] == {
            'briefId': 1,
            'briefResponseId': brief_response_id,
            'briefResponseAwardedValue': True
        }

    def test_can_change_awarded_brief_response_for_closed_brief_without_awarded_datestamp(self):
        self.setup_dummy_briefs(1, status="closed")
        self.setup_dummy_suppliers(1)
        brief_response1 = BriefResponse(brief_id=1, supplier_id=0, submitted_at=datetime.utcnow(), data={})
        brief_response2 = BriefResponse(brief_id=1, supplier_id=0, submitted_at=datetime.utcnow(), data={})
        brief_response1.award_details = {'pending': True}
        db.session.add_all([brief_response1, brief_response2])
        db.session.commit()
        brief_response1_id = brief_response1.id
        brief_response2_id = brief_response2.id
        # Update to be awarded to brief response 2 rather than brief response 1
        res = self._post_to_award_endpoint({'briefResponseId': brief_response2.id})
        assert res.status_code == 200

        brief_response_audits = get_audit_events(self.client, AuditTypes.update_brief_response)
        assert len(brief_response_audits) == 2
        assert brief_response_audits[0]['data'] == {
            'briefId': 1,
            'briefResponseId': brief_response1_id,
            'briefResponseAwardedValue': False
        }
        assert brief_response_audits[1]['data'] == {
            'briefId': 1,
            'briefResponseId': brief_response2_id,
            'briefResponseAwardedValue': True
        }

    def test_200_if_trying_to_award_a_brief_response_again_even_though_it_has_already_been_awarded(self):
        self.setup_dummy_briefs(1, status="closed")
        self.setup_dummy_suppliers(1)
        brief_response = BriefResponse(brief_id=1, supplier_id=0, submitted_at=datetime.utcnow(), data={})
        brief_response.award_details = {'pending': True}
        db.session.add(brief_response)
        db.session.commit()

        res = self._post_to_award_endpoint({'briefResponseId': brief_response.id})
        assert res.status_code == 200

    def test_400_if_no_updated_by_in_payload(self):
        res = self.client.post(
            self.award_url,
            data=json.dumps({"briefResponseId": 1}),
            content_type="application/json"
        )
        assert res.status_code == 400
        error = json.loads(res.get_data(as_text=True))['error']
        assert "'updated_by' is a required property" in error

    @pytest.mark.parametrize('status', ['draft', 'live', 'withdrawn', 'awarded', 'cancelled', 'unsuccessful'])
    def test_400_if_awarding_a_brief_response_to_a_non_closed_brief(self, status):
        self.setup_dummy_briefs(1, status=status)
        res = self._post_to_award_endpoint({'briefResponseId': 1})
        data = json.loads(res.get_data(as_text=True))
        assert res.status_code == 400
        assert data['error'] == "Brief is not closed"

    def test_400_if_awarding_a_draft_brief_response_to_a_closed_brief(self):
        self.setup_dummy_briefs(1, status="closed")
        self.setup_dummy_suppliers(1)
        brief_response = BriefResponse(brief_id=1, supplier_id=0, data={})
        db.session.add(brief_response)
        db.session.commit()

        res = self._post_to_award_endpoint({'briefResponseId': brief_response.id})
        data = json.loads(res.get_data(as_text=True))
        assert res.status_code == 400
        assert data['error'] == "BriefResponse cannot be awarded for this Brief"

    def test_400_if_awarding_a_brief_response_that_does_not_relate_to_that_brief(self):
        self.setup_dummy_briefs(2, status="closed")
        self.setup_dummy_suppliers(1)
        brief_response = BriefResponse(brief_id=2, supplier_id=0, submitted_at=datetime.utcnow(), data={})
        db.session.add(brief_response)
        db.session.commit()

        # We've set up brief response for brief ID 2 but attempt to award it for brief 1
        res = self._post_to_award_endpoint({'briefResponseId': brief_response.id})

        data = json.loads(res.get_data(as_text=True))
        assert res.status_code == 400
        assert data['error'] == "BriefResponse cannot be awarded for this Brief"


@mock.patch('app.main.views.briefs.index_brief')
class TestBriefAwardDetails(FrameworkSetupAndTeardown):

    award_url = "/briefs/1/award/{}/contract-details"
    valid_payload = {
        "awardDetails": {
            "awardedContractStartDate": "2020-12-31",
            "awardedContractValue": "99.95",
        },
        "updated_by": "user@email.com"
    }

    def _setup_brief_response(self, status='pending-awarded'):
        self.setup_dummy_briefs(1, status="closed")
        self.setup_dummy_suppliers(1)
        if status == 'draft':
            brief_response = BriefResponse(brief_id=1, supplier_id=0, data={})
        else:
            brief_response = BriefResponse(brief_id=1, supplier_id=0, submitted_at=datetime.utcnow(), data={})
        db.session.add(brief_response)
        db.session.commit()
        if status == 'pending-awarded':
            brief_response.award_details = {'pending': True}
            db.session.add(brief_response)
            db.session.commit()

        assert brief_response.status == status
        return brief_response.id

    def _post_to_award_details_endpoint(self, payload, brief_response_id):
        return self.client.post(
            self.award_url.format(brief_response_id),
            data=json.dumps(payload),
            content_type="application/json"
        )

    def test_can_supply_award_details_for_closed_brief_with_awarded_brief_response(self, index_brief):
        brief_response_id = self._setup_brief_response()

        res = self._post_to_award_details_endpoint(self.valid_payload, brief_response_id)
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert data['briefs']['awardedBriefResponseId'] == brief_response_id
        assert index_brief.called is True

        brief_response_audits = get_audit_events(self.client, AuditTypes.update_brief_response)
        assert len(brief_response_audits) == 1
        assert brief_response_audits[0]['data'] == {
            'briefId': 1,
            'briefResponseId': brief_response_id,
            'briefResponseAwardDetails': {
                "awardedContractStartDate": "2020-12-31",
                "awardedContractValue": "99.95"
            }
        }

    def test_can_supply_award_details_with_single_digit_dates(self, index_brief):
        brief_response_id = self._setup_brief_response()

        res = self._post_to_award_details_endpoint(
            {
                "awardDetails": {
                    "awardedContractStartDate": "2020-1-1",
                    "awardedContractValue": "99.95",
                },
                "updated_by": "user@email.com"
            }, brief_response_id
        )

        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert data['briefs']['awardedBriefResponseId'] == brief_response_id
        assert index_brief.called is True

        brief_response_audits = get_audit_events(self.client, AuditTypes.update_brief_response)
        assert len(brief_response_audits) == 1
        assert brief_response_audits[0]['data'] == {
            'briefId': 1,
            'briefResponseId': brief_response_id,
            'briefResponseAwardDetails': {
                "awardedContractStartDate": "2020-1-1",
                "awardedContractValue": "99.95"
            }
        }

    def test_edit_award_details_for_awarded_brief(self, index_brief):
        brief_response_id = self._setup_brief_response()

        self._post_to_award_details_endpoint(
            {
                "awardDetails": {
                    "awardedContractStartDate": "2020-12-31",
                    "awardedContractValue": "9900000.95",  # Wrong value
                },
                "updated_by": "user@email.com"
            },
            brief_response_id
        )
        assert BriefResponse.query.get(brief_response_id).status == 'awarded'

        # Fix the details
        res = self._post_to_award_details_endpoint(self.valid_payload, brief_response_id)
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert data['briefs']['awardedBriefResponseId'] == brief_response_id
        assert BriefResponse.query.get(brief_response_id).award_details == {
            "awardedContractStartDate": "2020-12-31",
            "awardedContractValue": "99.95",
        }
        assert index_brief.called

    @pytest.mark.parametrize('brief_response_status', ['draft', 'submitted'])
    def test_400_if_supplying_details_for_draft_or_submitted_brief_response(self, index_brief, brief_response_status):
        brief_response_id = self._setup_brief_response(status=brief_response_status)

        res = self._post_to_award_details_endpoint(self.valid_payload, brief_response_id)
        assert res.status_code == 400
        data = json.loads(res.get_data(as_text=True))
        assert data['error'] == "Cannot update award details for a Brief without a winning supplier"
        assert index_brief.called is False

    def test_400_if_award_details_payload_invalid(self, index_brief):
        brief_response_id = self._setup_brief_response()

        res = self._post_to_award_details_endpoint(
            {
                "awardDetails": {
                    "awardedContractValue": "I am not a number",
                    "awardedContractStartDate-day": None,
                    "awardedContractStartDate-month": None,
                    "awardedContractStartDate-year": None,
                },
                "updated_by": "user@email.com"
            }, brief_response_id
        )

        data = json.loads(res.get_data(as_text=True))
        assert res.status_code == 400
        assert data['error'] == {
            'awardedContractStartDate': 'answer_required',
            'awardedContractValue': 'not_money_format'
        }
        assert index_brief.called is False

    def test_400_if_no_updated_by_in_payload(self, index_brief):
        res = self._post_to_award_details_endpoint({
            "awardDetails": {
                "awardedContractStartDate": "2020-12-31",
                "awardedContractValue": "99.95"
            }
        }, 1)

        assert res.status_code == 400
        error = json.loads(res.get_data(as_text=True))['error']
        assert "'updated_by' is a required property" in error
        assert index_brief.called is False

    def test_404_if_brief_response_not_related_to_brief(self, index_brief):
        self.setup_dummy_briefs(2, status="closed")
        self.setup_dummy_suppliers(1)
        brief_response = BriefResponse(brief_id=2, supplier_id=0, submitted_at=datetime.utcnow(), data={})
        db.session.add(brief_response)
        db.session.commit()
        brief_response_id = brief_response.id

        res = self._post_to_award_details_endpoint(self.valid_payload, brief_response_id)

        assert res.status_code == 404
        assert index_brief.called is False

    def test_reverts_brief_to_pending(self, _index_brief):
        brief_response_id = self._setup_brief_response()

        self._post_to_award_details_endpoint(
            {
                "awardDetails": {
                    "awardedContractStartDate": "2020-12-31",
                    "awardedContractValue": "9900000.95",
                },
                "updated_by": "user@email.com"
            },
            brief_response_id
        )
        assert BriefResponse.query.get(brief_response_id).status == 'awarded'

        assert self.client.delete(
            self.award_url.format(brief_response_id),
            data=json.dumps({"updated_by": "user@email.com"}),
            content_type="application/json",
        ).status_code == 200
        assert BriefResponse.query.get(brief_response_id).status == 'pending-awarded'

        brief_response_audits = get_audit_events(self.client, AuditTypes.update_brief_response)
        assert brief_response_audits[-1]['data'] == {'briefId': 1,
                                                     'briefResponseAwardedValue': True,
                                                     'briefResponseId': brief_response_id,
                                                     'unAwardBriefDetails': True}
