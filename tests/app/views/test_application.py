import json
import mock
import time

from tests.app.helpers import BaseApplicationTest, INCOMING_APPLICATION_DATA

from app.models import db, Application, AuditEvent, User, utcnow, Agreement
from dmapiclient.audit import AuditTypes


class BaseApplicationsTest(BaseApplicationTest):
    def setup(self):
        super(BaseApplicationsTest, self).setup()

        with self.app.app_context():
            self.setup_dummy_user(id=0, role="applicant")
            self.setup_dummy_user(id=1, role="applicant")
            db.session.commit()

    def setup_dummy_application(self, data=None):
        if data is None:
            data = self.application_data
        with self.app.app_context():
            application = Application(
                data=data,
            )

            db.session.add(application)
            db.session.flush()

            application.submit_for_approval()
            db.session.commit()

            return application.id

    def setup_dummy_applicant(self, id, application_id):
        with self.app.app_context():
            if User.query.get(id):
                return id
            user = User(
                id=id,
                email_address="test+{}@digital.gov.au".format(id),
                name="my name",
                password="fake password",
                active=True,
                role='applicant',
                password_changed_at=utcnow(),
                application_id=application_id
            )
            db.session.add(user)
            db.session.commit()

            return user.id

    def setup_agreement(self):
        with self.app.app_context():
            agreement = Agreement(
                version='1.0',
                url='http://url',
                is_current=True
            )
            db.session.add(agreement)
            db.session.commit()

            return agreement.id

    def create_application(self, data):
        return self.client.post(
            '/applications',
            data=json.dumps({
                'updated_by': 'test@example.com',
                'application': data,
            }),
            content_type='application/json'
        )

    def patch_application(self, application_id, data):
        return self.client.patch(
            '/applications/{}'.format(application_id),
            data=json.dumps({
                'updated_by': 'test@example.com',
                'application': data,
            }),
            content_type='application/json'
        )

    def get_application(self, application_id):
        return self.client.get('/applications/{}'.format(application_id))

    def list_applications(self, **parameters):
        return self.client.get('/applications', query_string=parameters)

    def list_applications_with_task_status(self, **parameters):
        return self.client.get('/applications/tasks', query_string=parameters)

    def approve_application(self, application_id):
        return self.client.post(
            '/applications/{}/approve'.format(application_id),
            content_type='application/json')

    def reject_application(self, application_id):
        return self.client.post(
            '/applications/{}/approve'.format(application_id),
            content_type='application/json')

    def get_user(self, user_id):
        user = self.client.get('/users/{}'.format(user_id))
        return json.loads(user.get_data(as_text=True))['users']

    @property
    def application_data(self):
        return INCOMING_APPLICATION_DATA


class TestCreateApplication(BaseApplicationsTest):
    endpoint = '/applications'
    method = 'post'

    def test_create_new_application(self):
        res = self.create_application(
            dict(self.application_data)
        )

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 201, data

    def test_cannot_create_application_with_empty_json(self):
        res = self.client.post(
            '/applications',
            data=json.dumps({
                'updated_by': 'test@example.com',
            }),
            content_type='application/json'
        )

        assert res.status_code == 400


class TestApproveApplication(BaseApplicationsTest):
    def setup(self):
        super(TestApproveApplication, self).setup()
        self.application_id = self.setup_dummy_application(data=self.application_data)

    def search(self, query_body, **args):
        if args:
            params = '&'.join('{}={}'.format(k, urllib2.quote(v)) for k, v in args.items())
            q = "?{}".format(params)
        else:
            q = ''
        return self.client.get('/suppliers/search{}'.format(q),
                               data=json.dumps(query_body),
                               content_type='application/json')

    @mock.patch('app.jiraapi.JIRA')
    @mock.patch('app.main.views.applications.get_marketplace_jira')
    def test_application_assessments_and_domain_approvals(self, get_marketplace_jira, jira):
        self.patch_application(self.application_id, data={'status': 'saved'})
        a = self.get_application(self.application_id)
        user_id = self.setup_dummy_applicant(2, self.application_id)

        j = json.loads(a.get_data(as_text=True))['application']
        assert j['status'] == 'saved'

        a = self.approve_application(self.application_id)
        assert a.status_code == 400

        a = self.patch_application(self.application_id, data={'status': 'submitted'})
        j = json.loads(a.get_data(as_text=True))['application']
        assert j['status'] == 'submitted'

        a = self.approve_application(self.application_id)
        assert a.status_code == 200
        j = json.loads(a.get_data(as_text=True))['application']

        assert j['status'] == 'approved'
        assert 'supplier_code' in j
        assert j['supplier_code'] == j['supplier']['code']
        assert 'supplier' in j['links']

        user = self.get_user(user_id)
        assert user['role'] == 'supplier'
        assert user['supplier_code'] == j['supplier_code']

        a = self.get_application(self.application_id)
        assert a.status_code == 200
        j = json.loads(a.get_data(as_text=True))['application']

        assert j['status'] == 'approved'
        assert 'supplier_code' in j
        assert j['supplier_code'] == j['supplier']['code']
        assert 'supplier' in j['links']

        time.sleep(1)

        response = self.search({'query': {'term': {'code': j['supplier_code']}}})
        assert response.status_code == 200
        result = json.loads(response.get_data())
        assert result['hits']['total'] == 1
        assert len(result['hits']['hits']) == 1
        assert result['hits']['hits'][0]['_source']['code'] == j['supplier_code']

        a = self.get_application(self.application_id)
        assert a.status_code == 200
        j = json.loads(a.get_data(as_text=True))['application']

        a = self.list_applications()

        DUMMY_TASKS = {u'self': u'http://topissue'}

        mj = mock.Mock()
        mj.assessment_tasks_by_application_id.return_value = {self.application_id: DUMMY_TASKS}
        get_marketplace_jira.return_value = mj

        applist = self.list_applications_with_task_status()
        applist_j = json.loads(applist.get_data(as_text=True))
        assert applist_j['applications'][0]['tasks'] == DUMMY_TASKS


class TestUpdateApplication(BaseApplicationsTest):
    def setup(self):
        super(TestUpdateApplication, self).setup()

        self.application_id = self.setup_dummy_application(data=self.application_data)

    def test_patch_existing_order(self):
        application_data = self.application_data
        application_data['foo'] = 'baz'

        res = self.patch_application(
            application_id=self.application_id,
            data=application_data
        )

        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))
        assert data['application']['foo'] == 'baz'

    def test_empty_patch(self):
        res = self.patch_application(
            application_id=self.application_id,
            data={}
        )

        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))
        assert data['application']['foo'] == self.application_data['foo']

    def test_patch_missing_order(self):
        res = self.patch_application(
            application_id=9,
            data={}
        )

        assert res.status_code == 404

    def test_malformed_request(self):
        res = self.client.patch('/applications/1', data={'notAApplication': 'no'})
        assert res.status_code == 400

    def test_can_delete_a_application(self):
        delete = self.client.delete(
            '/applications/{}'.format(self.application_id),
            content_type='application/json')
        assert delete.status_code == 200

        fetch_again = self.client.get('/applications/{}'.format(self.application_id))
        assert fetch_again.status_code == 404


class TestGetApplication(BaseApplicationsTest):
    def setup(self):
        super(TestGetApplication, self).setup()

        self.application_id = self.setup_dummy_application()

    def test_get_application(self):
        res = self.get_application(self.application_id)

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['application']['id'] == self.application_id

    def test_get_missing_application_returns_404(self):
        res = self.get_application(999)

        assert res.status_code == 404


class TestListApplications(BaseApplicationsTest):
    def test_list_empty_applications(self):
        res = self.list_applications()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['applications'] == []
        assert 'self' in data['links'], data

    def test_list_applications(self):
        for i in range(3):
            self.setup_dummy_application()

        res = self.list_applications()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['applications']) == 3
        assert 'self' in data['links']

    def test_list_applications_pagination(self):
        for i in range(8):
            self.setup_dummy_application()

        res = self.list_applications()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['applications']) == 5
        assert 'next' in data['links']

        res = self.list_applications(page=2)
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['applications']) == 3
        assert 'prev' in data['links']

    def test_results_per_page(self):
        for i in range(8):
            self.setup_dummy_application()

        response = self.client.get('/applications?per_page=2')
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert 'applications' in data
        assert len(data['applications']) == 2

    def test_results_ordering(self):
        from itertools import tee, izip

        def pairwise(iterable):
            a, b = tee(iterable)
            next(b, None)
            return izip(a, b)

        def is_sorted(iterable, key=lambda a, b: a <= b):
            return all(key(a, b) for a, b in pairwise(iterable))

        for i in range(8):
            self.setup_dummy_application()

        response = self.client.get('/applications')
        data = json.loads(response.get_data())

        created_ats = [_['createdAt'] for _ in data['applications']]
        created_ats.reverse()
        assert is_sorted(created_ats)


class TestSubmitApplication(BaseApplicationsTest):
    def setup(self):
        super(TestSubmitApplication, self).setup()
        self.application_id = self.setup_dummy_application(data=self.application_data)

    def test_invalid_application_id(self):
        self.patch_application(self.application_id, data={'status': 'submitted'})

        response = self.client.post('/applications/{}/submit'.format(999))

        assert response.status_code == 404

    def test_application_already_submitted(self):
        self.patch_application(self.application_id, data={'status': 'submitted'})

        response = self.client.post('/applications/{}/submit'.format(self.application_id))

        assert response.status_code == 400
        assert 'Application is already submitted' in response.get_data()

    def test_application_unauthorized_user(self):
        self.patch_application(self.application_id, data={'status': 'saved'})
        application_id = self.setup_dummy_application(data=self.application_data)
        user_id = self.setup_dummy_applicant(2, application_id)
        self.setup_agreement()

        response = self.client.post(
            '/applications/{}/submit'.format(self.application_id),
            data=json.dumps({'user_id': user_id}),
            content_type='application/json')

        assert response.status_code == 400
        assert 'User is not authorized to submit application' in response.get_data()

    def test_no_current_agreeement(self):
        self.patch_application(self.application_id, data={'status': 'saved'})
        user_id = self.setup_dummy_applicant(2, self.application_id)

        response = self.client.post(
            '/applications/{}/submit'.format(self.application_id),
            data=json.dumps({'user_id': user_id}),
            content_type='application/json')

        assert response.status_code == 404

    def test_application_submitted(self):
        self.patch_application(self.application_id, data={'status': 'saved'})
        user_id = self.setup_dummy_applicant(2, self.application_id)
        self.setup_agreement()

        response = self.client.post(
            '/applications/{}/submit'.format(self.application_id),
            data=json.dumps({'user_id': user_id}),
            content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.get_data())

        assert data['application']['status'] == 'submitted'
        assert data['signed_agreement']['user_id'] == user_id
        with self.app.app_context():
            audit = AuditEvent.query.filter(
                AuditEvent.type == "submit_application"
            ).first()

            assert audit.object_id == self.application_id
