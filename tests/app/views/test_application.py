import json
from itertools import tee

import mock
import six
import pendulum

from app.models import (Agreement, Application, AuditEvent, Domain, Framework,
                        Product, User, db, utcnow)
from six.moves import zip as izip
from tests.app.helpers import BaseApplicationTest

application_data = {
    'number_of_employees': 'Sole trader',
    'status': 'saved',
    'contact_email': 'test@testseller.com',
    'contact_phone': '04044444040',
    'disclosures': {
        'conflicts_of_interest': 'no',
        'conflicts_of_interest_details': '',
        'insurance_claims': 'no',
        'insurance_claims_details': '',
        'investigations': 'no',
        'investigations_details': '',
        'legal_proceedings': 'no',
        'legal_proceedings_details': '',
        'other_circumstances': 'no',
        'other_circumstances_details': '',
        'structual_changes': 'no',
        'structual_changes_details': ''
    },
    'methodologies': 'abc',
    'tools': 'abc',
    'recruiter': 'no',
    'documents': {
        'financial': {
            'application_id': 1,
            'filename': '1.pdf'
        },
        'liability': {
            'application_id': 1,
            'expiry': pendulum.today().add(years=1).format('%Y-%m-%d'),
            'filename': '2.pdf'
        },
        'workers': {
            'application_id': 1,
            'expiry': pendulum.today().add(years=1).format('%Y-%m-%d'),
            'filename': '3.pdf'
        }
    },
    'services': {
        'Content and Publishing': True,
        'User research and Design': True
    },
    'pricing': {
        'Content and Publishing': {
            'maxPrice': '555'
        },
        'User research and Design': {
            'maxPrice': '555'
        }
    },
    'case_studies': {
        '0': {
            'approach': 'abc',
            'client': 'abc',
            'opportunity': 'abc',
            'outcome': [
                'abc'
            ],
            'project_links': [],
            'referee_contact': True,
            'referee_email': '234324234234',
            'referee_name': 'abc',
            'referee_position': 'abc',
            'roles': 'abc',
            'service': 'Content and Publishing',
            'status': 'unassessed',
            'supplier_code': 1,
            'timeframe': 'abc',
            'title': 'abc'
        },
        '1': {
            'approach': 'abc',
            'client': 'abc',
            'opportunity': 'abc',
            'outcome': [
                'abc'
            ],
            'project_links': [],
            'referee_contact': True,
            'referee_email': '234324234234',
            'referee_name': 'abc',
            'referee_position': 'abc',
            'roles': 'abc',
            'service': 'User research and Design',
            'status': 'unassessed',
            'supplier_code': 1,
            'timeframe': 'abc',
            'title': 'abc'
        }
    }
}


def test_approval(sample_submitted_application):
    a = sample_submitted_application
    assert a.supplier is None
    sample_submitted_application.set_approval(True)
    assert a.supplier is not None

    product_query = Product.query.filter(Product.supplier_code == a.supplier.code)
    products = product_query.all()
    assert a.supplier.products == products

    product_from_submitted = a.data['products']['0']
    product_from_submitted['id'] = products[0].id
    product_from_submitted['supplier_code'] = a.supplier.code
    product_from_submitted['links'] = {
        'self': '/products/{}'.format(products[0].id)
    }

    assert a.supplier.serializable['products'] == [product_from_submitted]
    assert 'recruitment' in a.supplier.serializable['seller_types']
    assert a.supplier.is_recruiter

    r_info = a.supplier.domains[0].recruiter_info._fieldsdict
    r_info_from_application = a.data['recruiter_info']['Strategy and Policy']

    assert six.viewitems(r_info) >= six.viewitems(r_info_from_application)

    assert six.viewitems(a.supplier.serializable['recruiter_info']) <= \
        six.viewitems(a.data['recruiter_info'])


class BaseApplicationsTest(BaseApplicationTest):
    def setup(self):
        super(BaseApplicationsTest, self).setup()

        with self.app.app_context():
            self.setup_dummy_user(id=0, role="applicant")
            self.setup_dummy_user(id=1, role="applicant")
            db.session.commit()

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
                'update_details': {'updated_by': 'test@example.com'},
                'application': data,
            }),
            content_type='application/json'
        )

    def patch_application(self, application_id, data):
        return self.client.patch(
            '/applications/{}'.format(application_id),
            data=json.dumps({
                'update_details': {'updated_by': 'test@example.com'},
                'application': data,
            }),
            content_type='application/json'
        )

    def get_application(self, application_id):
        return self.client.get('/applications/{}'.format(application_id))

    def list_applications(self, **parameters):
        return self.client.get('/applications', query_string=parameters)

    def list_applications_by_status(self, status):
        return self.client.get('/applications/status/{}'.format(status))

    def list_applications_with_task_status(self, **parameters):
        return self.client.get('/applications/tasks', query_string=parameters)

    def list_task_status(self, **parameters):
        return self.client.get('/tasks', query_string=parameters)

    def search_applications(self, keyword):
        return self.client.get('/applications/search/{}'.format(keyword))

    def approve_application(self, application_id):
        return self.client.post(
            '/applications/{}/approve'.format(application_id),
            data=json.dumps({
                'update_details': {'updated_by': 'test@example.com'}}),
            content_type='application/json')

    def reject_application(self, application_id):
        return self.client.post(
            '/applications/{}/reject'.format(application_id),
            data=json.dumps({
                'update_details': {'updated_by': 'test@example.com'}}),
            content_type='application/json')

    def revert_application(self, application_id):
        return self.client.post(
            '/applications/{}/revert'.format(application_id),
            data=json.dumps({
                'update_details': {'updated_by': 'test@example.com'}}),
            content_type='application/json')

    def get_user(self, user_id):
        user = self.client.get('/users/{}'.format(user_id))
        return json.loads(user.get_data(as_text=True))['users']


class TestCreateApplication(BaseApplicationsTest):
    endpoint = '/applications'
    method = 'post'

    @mock.patch('app.tasks.publish_tasks.application')
    def test_create_new_application(self, application):
        res = self.create_application(
            dict(self.application_data)
        )

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 201, data
        assert application.delay.called is True

    def test_cannot_create_application_with_empty_json(self):
        res = self.client.post(
            '/applications',
            data=json.dumps({
                'update_details': {'updated_by': 'test@example.com'},
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
    @mock.patch('app.emails.util.send_email')
    @mock.patch('app.tasks.publish_tasks.application')
    def test_application_assessments_and_domain_approvals(self, application, send_email, get_marketplace_jira, jira):
        with self.app.app_context():
            self.patch_application(self.application_id, data={'status': 'submitted'})
            a = self.reject_application(self.application_id)

            assert a.status_code == 200

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
            assert application.delay.called is True

            assert a.status_code == 200
            f = Framework.query.filter(
                Framework.slug == 'digital-marketplace'
            ).first()
            j = json.loads(a.get_data(as_text=True))['application']

            assert j['status'] == 'approved'
            assert 'supplier_code' in j
            assert j['supplier_code'] == j['supplier']['code']
            assert 'supplier' in j['links']
            assert j['supplier']['frameworks'][0]['framework_id'] == f.id

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
            mj.assessment_tasks_by_application_id.return_value = \
                {str(self.application_id): DUMMY_TASKS}
            get_marketplace_jira.return_value = mj

            applist = self.list_applications_with_task_status()
            applist_j = json.loads(applist.get_data(as_text=True))
            assert applist_j['applications'][0]['tasks'] == DUMMY_TASKS

            tasks = self.list_task_status()
            tasks_j = json.loads(tasks.get_data(as_text=True))['tasks']
            assert str(self.application_id) in tasks_j


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

    def test_patch_missing_order(self):
        res = self.patch_application(
            application_id=10,
            data={}
        )

        assert res.status_code == 404

    def test_malformed_request(self):
        res = self.client.patch('/applications/1', data={'notAApplication': 'no'})
        assert res.status_code == 400

    @mock.patch('app.tasks.publish_tasks.application')
    def test_can_delete_a_application(self, application):
        delete = self.client.delete(
            '/applications/{}'.format(self.application_id),
            data=json.dumps({
                'update_details': {'updated_by': 'test@example.com'}
            }),
            content_type='application/json')
        assert delete.status_code == 200
        assert application.delay.called is True

        fetch_again = self.client.get('/applications/{}'.format(self.application_id))
        assert fetch_again.status_code == 404


class TestGetApplication(BaseApplicationsTest):
    def setup(self):
        super(TestGetApplication, self).setup()
        self.application_id = self.setup_dummy_application()

        with self.app.app_context():
            db.session.add(
                Domain(name='test domain', ordering=1, price_minimum=123, price_maximum=1234, criteria_needed=1)
            )
            db.session.commit()

    def teardown(self):
        with self.app.app_context():
            Domain.query.filter(Domain.name == 'test domain').delete()
            db.session.commit()

        super(TestGetApplication, self).teardown()

    def test_get_application(self):
        res = self.get_application(self.application_id)

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['application']['id'] == self.application_id

    def test_get_missing_application_returns_404(self):
        res = self.get_application(999)

        assert res.status_code == 404

    def test_maximum_prices_are_returned_for_domains(self):
        res = self.get_application(self.application_id)
        data = json.loads(res.get_data(as_text=True))

        assert data['domains']['prices']['maximum']['test domain'] == '1234'


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

        with self.app.app_context():
            application = Application(
                data=self.application_data,
                status='deleted'
            )
            db.session.add(application)
            db.session.flush()
            db.session.commit()

            application = Application(
                data=self.application_data,
                status='saved'
            )
            db.session.add(application)
            db.session.flush()
            db.session.commit()

            res = self.list_applications()
            data = json.loads(res.get_data(as_text=True))

            assert res.status_code == 200
            assert len(data['applications']) == 4
            assert 'self' in data['links']

            res = self.list_applications_by_status(status='saved')
            data = json.loads(res.get_data(as_text=True))

            assert res.status_code == 200
            assert len(data['applications']) == 1
            assert 'self' in data['links']

    def test_list_applications_pagination(self):
        for i in range(8):
            self.setup_dummy_application()

        res = self.list_applications()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['applications']) == 5
        assert 'next' in data['links']
        assert 'last' in data['links']
        assert 'self' in data['links']

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

    def test_search_applications(self):
        applications_ids = []
        for i in range(8):
            id = self.setup_dummy_application()
            applications_ids.append(id)

        res = self.search_applications('bus')
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert len(data['applications']) == 5

        res = self.search_applications('invalid')
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert len(data['applications']) == 0

        res = self.search_applications(applications_ids[0])
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert len(data['applications']) == 1


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
        assert 'Application is already submitted' in response.get_data(as_text=True)

    @mock.patch('app.tasks.publish_tasks.application')
    def test_application_unauthorized_user(self, application):
        self.patch_application(self.application_id, data=application_data)
        application_id = self.setup_dummy_application(data=self.application_data)
        user_id = self.setup_dummy_applicant(2, application_id)
        self.setup_agreement()

        response = self.client.post(
            '/applications/{}/submit'.format(self.application_id),
            data=json.dumps({'user_id': user_id}),
            content_type='application/json')

        assert response.status_code == 400
        assert 'User is not authorized to submit application' in response.get_data(as_text=True)
        assert application.delay.called is True

    @mock.patch('app.tasks.publish_tasks.application')
    def test_no_current_agreeement(self, application):
        self.patch_application(self.application_id, data=application_data)
        user_id = self.setup_dummy_applicant(2, self.application_id)

        response = self.client.post(
            '/applications/{}/submit'.format(self.application_id),
            data=json.dumps({'user_id': user_id}),
            content_type='application/json')

        assert response.status_code == 404
        assert application.delay.called is True

    @mock.patch('app.jiraapi.JIRA')
    @mock.patch('app.tasks.publish_tasks.application')
    def test_application_submitted(self, application, jira):
        self.patch_application(self.application_id, data=application_data)
        user_id = self.setup_dummy_applicant(2, self.application_id)
        self.setup_agreement()

        response = self.client.post(
            '/applications/{}/submit'.format(self.application_id),
            data=json.dumps({'user_id': user_id}),
            content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert application.delay.called is True

        assert data['application']['status'] == 'submitted'
        assert data['signed_agreement']['user_id'] == user_id
        with self.app.app_context():
            audit = AuditEvent.query.filter(
                AuditEvent.type == "submit_application"
            ).first()

            assert audit.object_id == self.application_id


class TestRevertApplication(BaseApplicationsTest):
    def setup(self):
        super(TestRevertApplication, self).setup()
        self.application_id = self.setup_dummy_application(data=self.application_data)

    def test_invalid_application_id(self):
        self.patch_application(self.application_id, data={'status': 'submitted'})

        response = self.client.post('/applications/{}/revert'.format(999),
                                    data=json.dumps({
                                        'update_details': {'updated_by': 'test@example.com'}
                                    }),
                                    content_type='application/json')

        assert response.status_code == 404

    @mock.patch('app.tasks.publish_tasks.application')
    def test_application_already_reverted(self, application):
        self.patch_application(self.application_id, data={'status': 'saved'})

        response = self.client.post('/applications/{}/revert'.format(self.application_id),
                                    data=json.dumps({
                                        'update_details': {'updated_by': 'test@example.com'}
                                    }),
                                    content_type='application/json')

        assert response.status_code == 400
        assert 'not in submitted state for reverting' in response.get_data(as_text=True)
        assert application.delay.called is True

    def test_application_reverted(self):
        self.patch_application(self.application_id, data={'status': 'submitted'})

        response = self.client.post(
            '/applications/{}/revert'.format(self.application_id),
            data=json.dumps({
                'update_details': {'updated_by': 'test@example.com'},
                'message': 'revert message'
            }),
            content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.get_data())

        assert data['application']['status'] == 'saved'
        with self.app.app_context():
            audit = AuditEvent.query.filter(
                AuditEvent.type == "revert_application"
            ).first()

            assert audit.object_id == self.application_id
