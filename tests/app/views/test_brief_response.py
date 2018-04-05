import json
import pytest

from hypothesis import given

from ..helpers import BaseApplicationTest, JSONUpdateTestMixin
from ... import example_listings

from dmapiclient.audit import AuditTypes
from app.models import db, Lot, Brief, BriefResponse, AuditEvent, Service


class BaseBriefResponseTest(BaseApplicationTest):
    def setup(self):
        super(BaseBriefResponseTest, self).setup()

        with self.app.app_context():
            self.setup_dummy_suppliers(2)
            brief = Brief(
                data=example_listings.brief_data().example(),
                status='live', framework_id=5, lot=Lot.query.get(5)
            )

            service = Service(
                service_id='1234560987654321',
                data={'locations': [brief.data['location']]},
                status='published',
                framework_id=5,
                lot_id=5,
                supplier_code=0,
            )

            specialist_brief = Brief(
                data=example_listings.brief_data().example(),
                status='live', framework_id=5, lot=Lot.query.get(6)
            )

            specialist_service = Service(
                service_id='1234560987654322',
                data={'developerLocations': [specialist_brief.data['location']],
                      'developerPriceMin': "0",
                      'developerPriceMax': "1000"},
                status='published',
                framework_id=5,
                lot_id=6,
                supplier_code=0,
            )

            db.session.add_all([service, specialist_service, brief, specialist_brief])
            db.session.commit()

            self.brief_id = brief.id
            self.specialist_brief_id = specialist_brief.id

    def setup_dummy_brief_response(self, brief_id=None, supplier_code=0):
        with self.app.app_context():
            brief_response = BriefResponse(
                data=example_listings.brief_response_data().example(),
                supplier_code=supplier_code, brief_id=brief_id or self.brief_id
            )

            db.session.add(brief_response)
            db.session.commit()

            return brief_response.id

    def create_brief_response(self, data):
        return self.client.post(
            '/brief-responses',
            data=json.dumps({
                'updated_by': 'test@example.com',
                'briefResponses': data,
            }),
            content_type='application/json'
        )

    def get_brief_response(self, brief_response_id):
        return self.client.get('/brief-responses/{}'.format(brief_response_id))

    def list_brief_responses(self, **parameters):
        return self.client.get('/brief-responses', query_string=parameters)


class TestCreateBriefResponse(BaseBriefResponseTest, JSONUpdateTestMixin):
    endpoint = '/brief-responses'
    method = 'post'

    @pytest.mark.skip()
    @given(example_listings.brief_response_data())
    def test_create_new_brief_response(self, live_framework, brief_response_data):

        # tests for the case where the buggy frontend returns yaml
        # this case is handled with clean_non_strings in the brief response validator
        brief_response_data['essentialRequirements'][0] = True
        brief_response_data['niceToHaveRequirements'][0] = True

        res = self.create_brief_response(dict(brief_response_data, **{
            'briefId': self.brief_id,
            'supplierCode': 1,
        }))

        data = json.loads(res.get_data(as_text=True))

        ess = brief_response_data['essentialRequirements']
        nth = brief_response_data['niceToHaveRequirements']

        if all(ess):
            assert res.status_code == 201, data
            assert data['briefResponses']['supplierName'] == 'Supplier 1'
            assert data['briefResponses']['briefId'] == self.brief_id
        else:
            assert res.status_code == 400, data

    @pytest.mark.skip()
    @given(example_listings.brief_response_data())
    def test_create_brief_response_creates_an_audit_event(self, live_framework, brief_response_data):
        res = self.create_brief_response(dict(brief_response_data, **{
            'briefId': self.brief_id,
            'supplierCode': 1,
        }))

        ess = brief_response_data['essentialRequirements']
        nth = brief_response_data['niceToHaveRequirements']

        if all(ess):
            assert res.status_code == 201, res.get_data(as_text=True)
        else:
            assert res.status_code == 400, res.get_data(as_text=True)

        with self.app.app_context():
            audit_events = AuditEvent.query.filter(
                AuditEvent.type == AuditTypes.create_brief_response.value
            ).all()

        if all(ess):
            assert len(audit_events) == 1
            assert audit_events[0].data == {
                'briefResponseId': json.loads(res.get_data(as_text=True))['briefResponses']['id'],
                'briefResponseJson': dict(brief_response_data, **{
                    'briefId': self.brief_id,
                    'supplierCode': 1,
                })
            }
        else:
            assert len(audit_events) == 0

    def test_cannot_create_brief_response_with_empty_json(self, live_framework):
        res = self.client.post(
            '/brief-responses',
            data=json.dumps({
                'updated_by': 'test@example.com',
            }),
            content_type='application/json'
        )

        assert res.status_code == 400

    @pytest.mark.skip()
    def test_cannot_create_brief_response_with_invalid_json(self, live_framework):
        res = self.client.post(
            '/brief-responses',
            data=json.dumps({
                'updated_by': 'test@example.com',
                'briefResponses': {
                    'briefId': self.brief_id,
                    'supplierCode': 0,
                    'niceToHaveRequirements': 10
                }
            }),
            content_type='application/json'
        )

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error']['essentialRequirements'] == 'answer_required'
        assert 'niceToHaveRequirements' in data['error']

    def test_cannot_create_brief_response_without_supplier_code(self, live_framework):
        res = self.create_brief_response({
            'briefId': self.brief_id
        })

        assert res.status_code == 400
        assert 'supplierCode' in res.get_data(as_text=True)

    def test_cannot_create_brief_response_without_brief_id(self, live_framework):
        res = self.create_brief_response({
            'supplierCode': 0
        })

        assert res.status_code == 400
        assert 'briefId' in res.get_data(as_text=True)

    def test_cannot_create_brief_response_with_non_integer_supplier_code(self, live_framework):
        res = self.create_brief_response({
            'briefId': self.brief_id,
            'supplierCode': 'not a number',
        })

        assert res.status_code == 400
        assert 'Invalid supplier Code' in res.get_data(as_text=True)

    def test_cannot_create_brief_response_with_non_integer_brief_id(self, live_framework):
        res = self.create_brief_response({
            'briefId': 'not a number',
            'supplierCode': 0,
        })

        assert res.status_code == 400
        assert 'Invalid brief ID' in res.get_data(as_text=True)

    def test_cannot_create_brief_response_when_brief_doesnt_exist(self, live_framework):
        res = self.create_brief_response({
            'briefId': self.brief_id + 100,
            'supplierCode': 0
        })

        assert res.status_code == 400
        assert 'Invalid brief ID' in res.get_data(as_text=True)

    def test_cannot_create_brief_response_when_supplier_doesnt_exist(self, live_framework):
        res = self.create_brief_response({
            'briefId': self.brief_id,
            'supplierCode': 999
        })

        assert res.status_code == 400
        assert 'Invalid supplier Code' in res.get_data(as_text=True)

    def test_cannot_respond_to_a_brief_that_isnt_live(self, live_framework):
        with self.app.app_context():
            brief = Brief(
                data={}, status='draft', framework_id=5, lot=Lot.query.get(5)
            )
            db.session.add(brief)
            db.session.commit()

            brief_id = brief.id

        res = self.create_brief_response({
            'briefId': brief_id,
            'supplierCode': 0
        })

        assert res.status_code == 400
        assert "Brief must be live" in res.get_data(as_text=True)

    def test_cannot_respond_to_an_expired_framework_brief(self, expired_framework):
        res = self.create_brief_response({
            'briefId': self.brief_id,
            'supplierCode': 0
        })

        assert res.status_code == 400
        assert "Brief framework must be live" in res.get_data(as_text=True)

    @pytest.mark.skip()
    @given(example_listings.brief_response_data())
    def test_cannot_respond_to_a_brief_more_than_once_from_the_same_supplier(self, live_framework, brief_response_data):
        ess = brief_response_data['essentialRequirements']
        nth = brief_response_data['niceToHaveRequirements']

        if all(ess) and all(nth):
            self.create_brief_response(dict(brief_response_data, **{
                'briefId': self.brief_id,
                'supplierCode': 0,
            }))

            res = self.create_brief_response(dict(brief_response_data, **{
                'briefId': self.brief_id,
                'supplierCode': 0,
            }))

            assert res.status_code == 400, res.get_data(as_text=True)
            assert 'Brief response already exists' in res.get_data(as_text=True)

    @pytest.mark.skip()
    @given(example_listings.brief_response_data(None, 5).filter(
        lambda x: len(x['essentialRequirements']) != 5 and all(i is not None for i in x['essentialRequirements'])))
    def test_cannot_respond_to_a_brief_with_wrong_number_of_essential_reqs(self, live_framework, brief_response_data):
        res = self.create_brief_response(dict(brief_response_data, **{
            'briefId': self.brief_id,
            'supplierCode': 0,
        }))

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400, res.get_data(as_text=True)
        assert data['error']['essentialRequirements'] == 'answer_required'

    @pytest.mark.skip()
    @given(example_listings.brief_response_data(5, None).filter(
        lambda x: len(x['niceToHaveRequirements']) != 5 and all(i is not None for i in x['niceToHaveRequirements'])))
    def test_cannot_respond_to_a_brief_with_wrong_number_of_nicetohave_reqs(self, live_framework, brief_response_data):
        res = self.create_brief_response(dict(brief_response_data, **{
            'briefId': self.brief_id,
            'supplierCode': 0,
        }))

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400, res.get_data(as_text=True)
        assert data['error']['niceToHaveRequirements'] == 'answer_required'

    @pytest.mark.skip()
    @given(example_listings.brief_response_data(5, None).filter(
        lambda x: any(i is None for i in x['niceToHaveRequirements'])))
    def test_cannot_respond_to_a_brief_with_none_reqs_values(self, live_framework, brief_response_data):
        res = self.create_brief_response(dict(brief_response_data, **{
            'briefId': self.brief_id,
            'supplierCode': 0,
        }))

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400, res.get_data(as_text=True)
        assert data['error']['niceToHaveRequirements'] == "answer_required"

    @given(example_listings.specialists_brief_response_data())
    @pytest.mark.skip(reason='fails randomly and sporadically')
    def test_create_digital_specialists_brief_response(self, live_framework, brief_response_data):
        ess = brief_response_data['essentialRequirements']
        nth = brief_response_data['niceToHaveRequirements']

        res = self.create_brief_response(dict(brief_response_data, **{
            'briefId': self.specialist_brief_id,
            'supplierCode': 0,
        }))

        data = json.loads(res.get_data(as_text=True))

        if all(ess):
            assert res.status_code == 201, data
        else:
            assert res.status_code == 400, data


class TestGetBriefResponse(BaseBriefResponseTest):
    def setup(self):
        super(TestGetBriefResponse, self).setup()

        self.brief_response_id = self.setup_dummy_brief_response()

    def test_get_brief_response(self):
        res = self.get_brief_response(self.brief_response_id)

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['briefResponses']['id'] == self.brief_response_id
        assert data['briefResponses']['supplierCode'] == 0

    def test_get_missing_brief_returns_404(self):
        res = self.get_brief_response(999)

        assert res.status_code == 404


class TestListBriefResponses(BaseBriefResponseTest):
    def test_list_empty_brief_responses(self):
        res = self.list_brief_responses()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['briefResponses'] == []
        assert 'self' in data['links'], data

    def test_list_brief_responses(self):
        for i in range(3):
            self.setup_dummy_brief_response()

        res = self.list_brief_responses()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefResponses']) == 3
        assert 'self' in data['links']

    def test_list_brief_responses_creates_an_audit_event(self):
        for i in range(3):
            self.setup_dummy_brief_response()

        res = self.client.get(
            '/brief-responses',
            environ_base={'HTTP_USER_AGENT': 'DM-API-Client/123'},
            query_string={'brief_id': 1}
        )
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        with self.app.app_context():
            audit_events = AuditEvent.query.filter(
                AuditEvent.type == AuditTypes.read_brief_responses.value
            ).all()

        assert len(audit_events) == 1

    def test_list_brief_responses_does_not_create_an_audit_event_wrong_user_agent(self):
        for i in range(3):
            self.setup_dummy_brief_response()

        res = self.client.get(
            '/brief-responses',
            environ_base={'HTTP_USER_AGENT': 'SomethingElse'},
            query_string={'brief_id': 1}
        )
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        with self.app.app_context():
            audit_events = AuditEvent.query.filter(
                AuditEvent.type == AuditTypes.read_brief_responses.value
            ).all()

        assert len(audit_events) == 0

    def test_list_brief_responses_pagination(self):
        for i in range(8):
            self.setup_dummy_brief_response()

        res = self.list_brief_responses()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefResponses']) == 5
        assert 'next' in data['links']

        res = self.list_brief_responses(page=2)
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefResponses']) == 3
        assert 'prev' in data['links']

    @pytest.mark.skipif(True, reason="failing for AU")
    def test_list_brief_responses_for_supplier_code(self):
        for i in range(8):
            self.setup_dummy_brief_response(supplier_code=0)
            self.setup_dummy_brief_response(supplier_code=1)

        res = self.list_brief_responses(supplier_code=1)
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefResponses']) == 8
        assert all(br['supplierCode'] == 1 for br in data['briefResponses'])
        assert 'self' in data['links']

    def test_list_brief_responses_for_brief_id(self):
        with self.app.app_context():
            brief = Brief(
                data=example_listings.brief_data().example(),
                status='live', framework_id=5, lot=Lot.query.get(5)
            )
            db.session.add(brief)
            db.session.commit()

            another_brief_id = brief.id

        for i in range(8):
            self.setup_dummy_brief_response(brief_id=self.brief_id, supplier_code=0)
            self.setup_dummy_brief_response(brief_id=another_brief_id, supplier_code=0)

        res = self.list_brief_responses(brief_id=another_brief_id)
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['briefResponses']) == 8
        assert all(br['briefId'] == another_brief_id for br in data['briefResponses'])
        assert 'self' in data['links']

    def test_cannot_list_brief_responses_for_non_integer_brief_id(self):
        res = self.list_brief_responses(brief_id="not-valid")
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == 'Invalid brief_id: not-valid'

    def test_cannot_list_brief_responses_for_non_integer_supplier_code(self):
        res = self.list_brief_responses(supplier_code="not-valid")
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == 'Invalid supplier_code: not-valid'
