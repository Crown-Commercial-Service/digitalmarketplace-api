import json

from tests.app.helpers import BaseApplicationTest

from app.models import db, Project


class BaseProjectTest(BaseApplicationTest):
    def setup(self):
        super(BaseProjectTest, self).setup()

    def setup_dummy_project(self, data=None):
        if data is None:
            data = self.project_data
        with self.app.app_context():

            project = Project(
                data=data
            )

            db.session.add(project)
            db.session.commit()

            return project.id

    def create_project(self, data):
        return self.client.post(
            '/projects',
            data=json.dumps({
                'updated_by': 'test@example.com',
                'project': data,
            }),
            content_type='application/json'
        )

    def patch_project(self, project_id, data):
        return self.client.patch(
            '/projects/{}'.format(project_id),
            data=json.dumps({
                'updated_by': 'test@example.com',
                'project': data,
            }),
            content_type='application/json'
        )

    def get_project(self, project_id):
        return self.client.get('/projects/{}'.format(project_id))

    def list_projects(self, **parameters):
        return self.client.get('/projects', query_string=parameters)

    @property
    def project_data(self):
        return {'foo': 'bar'}


class TestCreateProject(BaseProjectTest):
    endpoint = '/projects'
    method = 'post'

    def test_create_new_project(self):
        res = self.create_project(
            dict(self.project_data)
        )

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 201, data

    def test_cannot_create_project_with_empty_json(self):
        res = self.client.post(
            '/projects',
            data=json.dumps({
                'updated_by': 'test@example.com',
            }),
            content_type='application/json'
        )

        assert res.status_code == 400


class TestUpdateProject(BaseProjectTest):

    def setup(self):
        super(TestUpdateProject, self).setup()

        self.project_id = self.setup_dummy_project(data=self.project_data)

    def test_patch_existing_order(self):
        project_data = self.project_data
        project_data['foo'] = 'baz'

        res = self.patch_project(
            project_id=self.project_id,
            data=project_data
        )

        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))
        assert data['project']['foo'] == 'baz'

    def test_empty_patch(self):
        res = self.patch_project(
            project_id=self.project_id,
            data={}
        )

        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))
        assert data['project']['foo'] == self.project_data['foo']

    def test_patch_missing_order(self):
        res = self.patch_project(
            project_id=9,
            data={}
        )

        assert res.status_code == 404

    def test_malformed_request(self):
        res = self.client.patch('/projects/1', data={'notAProject': 'no'})
        assert res.status_code == 400


class TestGetProject(BaseProjectTest):
    def setup(self):
        super(TestGetProject, self).setup()

        self.project_id = self.setup_dummy_project()

    def test_get_project(self):
        res = self.get_project(self.project_id)

        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['project']['id'] == self.project_id

    def test_get_missing_project_returns_404(self):
        res = self.get_project(999)

        assert res.status_code == 404


class TestListProjects(BaseProjectTest):
    def test_list_empty_projects(self):
        res = self.list_projects()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['projects'] == []
        assert 'self' in data['links'], data

    def test_list_projects(self):
        for i in range(3):
            self.setup_dummy_project()

        res = self.list_projects()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['projects']) == 3
        assert 'self' in data['links']

    def test_list_projects_pagination(self):
        for i in range(8):
            self.setup_dummy_project()

        res = self.list_projects()
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['projects']) == 5
        assert 'next' in data['links']

        res = self.list_projects(page=2)
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['projects']) == 3
        assert 'prev' in data['links']

    def test_results_per_page(self):
        for i in range(8):
            self.setup_dummy_project()

        response = self.client.get('/projects?per_page=2')
        assert response.status_code == 200
        data = json.loads(response.get_data())
        assert 'projects' in data
        assert len(data['projects']) == 2
