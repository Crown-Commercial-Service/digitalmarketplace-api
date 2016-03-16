import json

import mock
from ..helpers import BaseApplicationTest, COMPLETE_DIGITAL_SPECIALISTS_BRIEF

from dmapiclient.audit import AuditTypes
from app import db
from app.models import Framework


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
                        'emailAddress': 'test+1@digital.gov.uk',
                        'name': 'my name',
                        'role': 'buyer',
                        'active': True,
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
        assert not data['briefs']['clarificationQuestionsAreClosed']

    def test_get_brief_returns_404_if_not_found(self):
        res = self.client.get('/briefs/1')

        assert res.status_code == 404

    def test_list_briefs(self):
        self.setup_dummy_briefs(3)

        res = self.client.get('/briefs')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == 3

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
        assert len(data['briefs']) == 3, data['briefs']

    def test_cannot_list_briefs_by_invalid_status(self):
        self.setup_dummy_briefs(1, status='live')
        self.setup_dummy_briefs(1, status='draft', brief_start=2)

        res = self.client.get('/briefs?status=invalid')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == 0

    def test_list_briefs_by_multiple_statuses(self):
        self.setup_dummy_briefs(3, status='live')
        self.setup_dummy_briefs(2, status='draft', brief_start=4)

        res = self.client.get('/briefs?status=draft,live')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == 5, data['briefs']

    def test_list_briefs_by_framework(self):
        self.setup_dummy_briefs(3, status='live')
        self.setup_dummy_briefs(2, status='draft', brief_start=4)

        res = self.client.get('/briefs?framework=digital-outcomes-and-specialists')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == 5, data['briefs']

    def test_cannot_list_briefs_by_invalid_framework(self):
        self.setup_dummy_briefs(1, status='live')
        self.setup_dummy_briefs(1, status='draft', brief_start=2)

        res = self.client.get('/briefs?framework=digital-biscuits-and-cakes')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == 0

    def test_list_briefs_by_framework_and_status(self):
        self.setup_dummy_briefs(3, status='live')
        self.setup_dummy_briefs(2, status='draft', brief_start=4)

        res = self.client.get('/briefs?framework=digital-outcomes-and-specialists&status=draft')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == 2, data['briefs']

    def test_list_briefs_by_lot(self):
        self.setup_dummy_briefs(3, status='live', lot='digital-outcomes')
        self.setup_dummy_briefs(1, status='draft', lot='digital-outcomes', brief_start=4)
        self.setup_dummy_briefs(2, status='live', lot='digital-specialists', brief_start=5)

        res = self.client.get('/briefs?lot=digital-outcomes')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == 4, data['briefs']

    def test_list_briefs_by_lot_and_status(self):
        self.setup_dummy_briefs(3, status='live', lot='digital-outcomes')
        self.setup_dummy_briefs(1, status='draft', lot='digital-outcomes', brief_start=4)
        self.setup_dummy_briefs(2, status='live', lot='digital-specialists', brief_start=5)

        res = self.client.get('/briefs?lot=digital-outcomes&status=live')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefs']) == 3, data['briefs']

    def test_list_briefs_pagination_page_one(self):
        self.setup_dummy_briefs(7)

        res = self.client.get('/briefs')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        assert len(data['briefs']) == 5
        assert data['links']['next'] == 'http://localhost/briefs?page=2'
        assert data['links']['last'] == 'http://localhost/briefs?page=2'

    def test_list_briefs_pagination_page_two(self):
        self.setup_dummy_briefs(7)

        res = self.client.get('/briefs?page=2')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        assert len(data['briefs']) == 2
        assert data['links']['prev'] == 'http://localhost/briefs?page=1'

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
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        res = self.client.get('/briefs/1')
        published_at = json.loads(res.get_data(as_text=True))['briefs']['publishedAt']
        assert published_at == original_published_at

    def test_cannot_make_a_brief_live_if_the_framework_is_no_longer_live(self):
        self.setup_dummy_briefs(1, title='The title')

        with self.app.app_context():
            framework = Framework.query.get(5)
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

    def test_cannot_return_a_live_brief_to_pending(self):
        self.setup_dummy_briefs(1, status='live')

        res = self.client.put(
            '/briefs/1/status',
            data=json.dumps({
                'briefs': {'status': 'draft'},
                'update_details': {'updated_by': 'example'}
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == "Cannot change brief status from 'live' to 'draft'"

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
        assert data['error'] == "Invalid brief status 'invalid'"

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
