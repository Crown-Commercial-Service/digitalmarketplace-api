import json

from tests.app.helpers import BaseApplicationTest

from app.models import db, CaseStudy


class BaseCaseStudyTest(BaseApplicationTest):
    def setup(self):
        super(BaseCaseStudyTest, self).setup()

        with self.app.app_context():
            self.setup_dummy_suppliers(2)
            db.session.commit()

    def setup_dummy_case_study(self, supplier_code=0, data=None):
        if data is None:
            data = self.case_study_data
        with self.app.app_context():

            case_study = CaseStudy(
                data=data,
                supplier_code=supplier_code
            )

            db.session.add(case_study)
            db.session.commit()

            return case_study.id

    def create_case_study(self, data):
        return self.client.post(
            '/case-studies',
            data=json.dumps({
                'updated_by': 'test@example.com',
                'caseStudy': data,
            }),
            content_type='application/json'
        )

    def patch_case_study(self, case_study_id, data):
        return self.client.patch(
            '/case-studies/{}'.format(case_study_id),
            data=json.dumps({
                'updated_by': 'test@example.com',
                'caseStudy': data,
            }),
            content_type='application/json'
        )

    def get_case_study(self, case_study_id):
        return self.client.get('/case-studies/{}'.format(case_study_id))

    def list_case_studies(self, **parameters):
        return self.client.get('/case-studies', query_string=parameters)

    @property
    def case_study_data(self):
        return {'foo': 'bar'}


class TestCreateCaseStudy(BaseCaseStudyTest):
    endpoint = '/case-studies'
    method = 'post'

    def test_create_new_case_study(self):
        res = self.create_case_study(
            dict(self.case_study_data, supplierCode=0)
        )

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 201, data
        assert data['caseStudy']['supplierName'] == 'Supplier 0'

    def test_cannot_create_case_study_with_empty_json(self):
        res = self.client.post(
            '/case-studies',
            data=json.dumps({
                'updated_by': 'test@example.com',
            }),
            content_type='application/json'
        )

        assert res.status_code == 400

    def test_cannot_create_case_study_without_supplier_code(self):
        res = self.create_case_study({
        })

        assert res.status_code == 400
        assert 'supplierCode' in res.get_data(as_text=True)

    def test_cannot_create_case_study_with_non_integer_supplier_code(self):
        res = self.create_case_study({
            'supplierCode': 'not a number',
        })

        assert res.status_code == 400
        assert 'Invalid supplier Code' in res.get_data(as_text=True)

    def test_cannot_create_case_study_when_supplier_doesnt_exist(self):
        res = self.create_case_study({
            'supplierCode': 999
        })

        assert res.status_code == 400
        assert 'Invalid supplier Code' in res.get_data(as_text=True)


class TestUpdateCaseStudy(BaseCaseStudyTest):

    def setup(self):
        super(TestUpdateCaseStudy, self).setup()

        self.case_study_id = self.setup_dummy_case_study(supplier_code=0, data=self.case_study_data)

    def test_patch_existing_order(self):
        case_study_data = self.case_study_data
        case_study_data['foo'] = 'baz'

        res = self.patch_case_study(
            case_study_id=self.case_study_id,
            data=case_study_data
        )

        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))
        assert data['caseStudy']['supplierName'] == 'Supplier 0'
        assert data['caseStudy']['foo'] == 'baz'

    def test_empty_patch(self):
        res = self.patch_case_study(
            case_study_id=self.case_study_id,
            data={}
        )

        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))
        assert data['caseStudy']['supplierName'] == 'Supplier 0'
        assert data['caseStudy']['foo'] == self.case_study_data['foo']

    def test_patch_missing_order(self):
        res = self.patch_case_study(
            case_study_id=9,
            data={}
        )

        assert res.status_code == 404

    def test_malformed_request(self):
        res = self.client.patch('/case-studies/1', data={'notACaseStudy': 'no'})
        assert res.status_code == 400

    def test_can_delete_a_case_study(self):
        delete = self.client.delete(
            '/case-studies/{}'.format(self.case_study_id),
            data=json.dumps({'update_details': {'updated_by': 'deleter'}}),
            content_type='application/json')
        assert delete.status_code == 200

        audit_response = self.client.get('/audit-events')
        assert audit_response.status_code == 200
        audit_data = json.loads(audit_response.get_data(as_text=True))
        assert len(audit_data['auditEvents']) == 1
        assert audit_data['auditEvents'][0]['type'] == 'delete_casestudy'
        assert audit_data['auditEvents'][0]['user'] == 'deleter'
        assert audit_data['auditEvents'][0]['data']['caseStudyId'] == self.case_study_id

        fetch_again = self.client.get('/case-studies/{}'.format(self.case_study_id))
        assert fetch_again.status_code == 404


class TestGetCaseStudy(BaseCaseStudyTest):
    def setup(self):
        super(TestGetCaseStudy, self).setup()

        self.case_study_id = self.setup_dummy_case_study()

    def test_get_case_study(self):
        res = self.get_case_study(self.case_study_id)

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['caseStudy']['id'] == self.case_study_id
        assert data['caseStudy']['supplierCode'] == 0

    def test_get_supplier_with_case_study(self):
        res = self.client.get('/suppliers/0')

        data = json.loads(res.get_data())
        assert res.status_code == 200
        assert data['supplier']['code'] == 0
        assert data['supplier']['case_study_ids'][0] == self.case_study_id

    def test_get_missing_case_study_returns_404(self):
        res = self.get_case_study(999)

        assert res.status_code == 404


class TestListCaseStudies(BaseCaseStudyTest):
    def test_list_empty_case_studies(self):
        res = self.list_case_studies()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['caseStudies'] == []
        assert 'self' in data['links'], data

    def test_list_case_studies(self):
        for i in range(3):
            self.setup_dummy_case_study()

        res = self.list_case_studies()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['caseStudies']) == 3
        assert 'self' in data['links']

    def test_list_case_studies_pagination(self):
        for i in range(8):
            self.setup_dummy_case_study()

        res = self.list_case_studies()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['caseStudies']) == 5
        assert 'next' in data['links']

        res = self.list_case_studies(page=2)
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['caseStudies']) == 3
        assert 'prev' in data['links']

    def test_results_per_page(self):
        for i in range(8):
            self.setup_dummy_case_study()

        response = self.client.get('/case-studies?per_page=2')
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert 'caseStudies' in data
        assert len(data['caseStudies']) == 2

    def test_list_case_studies_for_supplier_code(self):
        for i in range(3):
            self.setup_dummy_case_study(supplier_code=0)
            self.setup_dummy_case_study(supplier_code=1)

        res = self.list_case_studies(supplier_code=1)
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['caseStudies']) == 3
        assert all(br['supplierCode'] == 1 for br in data['caseStudies'])
        assert 'self' in data['links']

    def test_cannot_list_case_studies_for_non_integer_supplier_code(self):
        res = self.list_case_studies(supplier_code="not-valid")
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 400
        assert data['error'] == 'Invalid supplier_code: not-valid'
