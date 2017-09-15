import json
from datetime import datetime
import math
import random

import pytest
from tests.helpers import FixtureMixin
from tests.bases import BaseApplicationTest

from dmapiclient.audit import AuditTypes
from app.models import DATETIME_FORMAT, AuditEvent, User
from app.models.direct_award import DirectAwardProjectUser, DirectAwardSearch, DirectAwardProject
from ...helpers import DIRECT_AWARD_SEARCH_URL, DIRECT_AWARD_PROJECT_NAME


class DirectAwardSetupAndTeardown(BaseApplicationTest, FixtureMixin):
    def setup(self):
        super(DirectAwardSetupAndTeardown, self).setup()
        self.user_id = self.setup_dummy_user(id=1, role='buyer')
        self.direct_award_project_name = DIRECT_AWARD_PROJECT_NAME
        self.direct_award_search_url = DIRECT_AWARD_SEARCH_URL

    def teardown(self):
        super(DirectAwardSetupAndTeardown, self).teardown()


class TestDirectAwardListProjects(DirectAwardSetupAndTeardown):
    def setup(self):
        super(TestDirectAwardListProjects, self).setup()
        self.project_id = self.create_direct_award_project(user_id=self.user_id,
                                                           project_name=self.direct_award_project_name)

    def test_list_projects_200s_with_user_id(self):
        res = self.client.get('/direct-award/projects?user-id={}'.format(self.user_id))
        assert res.status_code == 200

    def test_list_projects_returns_all_projects_for_user(self):
        self.create_direct_award_project(user_id=self.user_id, project_id=self.project_id + 1)

        # Create a project for another user, i.e. one that shouldn't be returned
        self.setup_dummy_user(id=self.user_id + 1, role='buyer')
        self.create_direct_award_project(user_id=self.user_id + 1, project_id=self.project_id + 2)

        res = self.client.get('/direct-award/projects?user-id={}'.format(self.user_id))
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['projects']) == 2

        with self.app.app_context():
            projects = DirectAwardProject.query.filter(DirectAwardProject.users.any(User.id == self.user_id))

            assert all([project.serialize() in data['projects'] for project in projects.all()])
            assert data['meta']['total'] == len(projects.all())
            assert data['meta']['total'] < len(DirectAwardProject.query.all())

    @pytest.mark.parametrize('page_size, extra_projects',
                             ((1, 0),  # Page size == number of projects, shouldn't paginate
                              (2, 0),  # Page size > number of projects, shouldn't paginate
                              (2, 2),  # Page size < number of projects, should paginate (pages=2)
                              (2, 9),  # Page size < number of projects, should paginate (pages=5)
                              ))
    def test_list_projects_paginates_and_links_correctly(self, page_size, extra_projects):
        self.app.config['DM_API_PROJECTS_PAGE_SIZE'] = page_size

        for i in range(extra_projects):
            self.create_direct_award_project(user_id=self.user_id, project_id=self.project_id + i + 1)

        res = self.client.get('/direct-award/projects?user-id={}'.format(self.user_id))
        data = json.loads(res.get_data(as_text=True))

        num_pages = math.ceil((extra_projects + 1) / page_size)
        if num_pages > 1:
            assert data['links']['last'].endswith('&page={}'.format(num_pages))
            assert 'next' in data['links']

        else:
            assert 'last' not in data['links']
            assert 'next' not in data['links']

    def test_list_projects_accepts_page_offset(self):
        self.app.config['DM_API_PROJECTS_PAGE_SIZE'] = 2

        for i in range(10):
            self.create_direct_award_project(user_id=self.user_id, project_id=self.project_id + i)

        projects_seen = []
        pages = 5
        for i in range(pages):
            res = self.client.get('/direct-award/projects?user-id={}&page={}'.format(self.user_id, i + 1))
            data = json.loads(res.get_data(as_text=True))

            for project in data['projects']:
                projects_seen.append(project['id'])

        assert len(set(projects_seen)) == self.app.config['DM_API_PROJECTS_PAGE_SIZE'] * pages

    def test_list_projects_orders_by_id(self):
        self.app.config['DM_API_PROJECTS_PAGE_SIZE'] = 2

        i = 1
        while i <= 10:
            self.create_direct_award_project(user_id=self.user_id, project_id=self.project_id + i,
                                             created_at=datetime(2017, 1, 1, 0, 0, 0))
            i += 1

        last_seen = 0
        for i in range(5):
            res = self.client.get('/direct-award/projects?user-id={}&page={}'.format(self.user_id, i + 1))
            data = json.loads(res.get_data(as_text=True))

            # Check that each project has a created_at date older than the last, i.e. reverse chronological order.
            for project in data['projects']:
                assert last_seen < project['id']

    def test_list_projects_orders_by_created_at_descending(self):
        self.app.config['DM_API_PROJECTS_PAGE_SIZE'] = 2

        # Randomly shuffled list of years for created_at timestamps
        created_at_years = [2016 - i for i in range(10)]
        random.shuffle(created_at_years)

        i = 1
        while i <= 10:
            self.create_direct_award_project(user_id=self.user_id, project_id=self.project_id + i,
                                             created_at=datetime(created_at_years.pop(), 1, 1, 0, 0, 0))
            i += 1

        last_seen_datetime = None
        for i in range(5):
            res = self.client.get('/direct-award/projects?user-id={}&page={}'
                                  '&latest-first=true'.format(self.user_id, i + 1))
            data = json.loads(res.get_data(as_text=True))

            # Check that each project has a created_at date older than the last, i.e. reverse chronological order.
            for project in data['projects']:
                next_datetime = datetime.strptime(project['createdAt'], DATETIME_FORMAT)

                if last_seen_datetime:
                    assert next_datetime < last_seen_datetime

                last_seen_datetime = next_datetime

    def test_list_projects_returns_serialized_project_with_metadata(self):
        res = self.client.get('/direct-award/projects?user-id={}'.format(self.user_id))
        data = json.loads(res.get_data(as_text=True))

        assert 'projects' in data
        assert data['meta']['total'] == 1
        assert len(data['projects']) == 1

        with self.app.app_context():
            assert data['projects'][0] == DirectAwardProject.query.get(self.project_id).serialize()


class TestDirectAwardCreateProject(DirectAwardSetupAndTeardown):
    def _create_project_data(self):
        return {
            'project': {
                'userId': self.user_id,
                'name': self.direct_award_project_name,
            },
            'updated_by': str(self.user_id)
        }.copy()

    @pytest.mark.parametrize('drop_project_keys, expected_status',
                             (
                                 ([], 201),  # All required keys
                                 (['updated_by'], 400))  # Don't send updated_by
                             )
    def test_create_project_requires_updated_by(self, drop_project_keys, expected_status):
        project_data = self._create_project_data()
        for key in drop_project_keys:
            del project_data[key]

        res = self.client.post('/direct-award/projects',
                               data=json.dumps(project_data),
                               content_type='application/json')
        assert res.status_code == expected_status

    @pytest.mark.parametrize('drop_project_keys, expected_status',
                             (
                                 ([], 201),  # All required keys
                                 (['userId'], 400),  # Don't send user_id
                                 (['name'], 400),  # Don't send project name
                                 (['userId', 'name'], 400))  # Don't send user_id or name
                             )
    def test_create_project_requires_project_key_with_name_and_user_id(self, drop_project_keys, expected_status):
        project_data = self._create_project_data()
        for key in drop_project_keys:
            del project_data['project'][key]

        res = self.client.post('/direct-award/projects',
                               data=json.dumps(project_data),
                               content_type='application/json')
        assert res.status_code == expected_status

    def test_create_project_creates_project_user(self):
        project_data = self._create_project_data()

        with self.app.app_context():
            assert len(DirectAwardProjectUser.query.all()) == 0

        res = self.client.post('/direct-award/projects', data=json.dumps(project_data), content_type='application/json')

        assert res.status_code == 201

        with self.app.app_context():
            assert len(DirectAwardProjectUser.query.all()) == 1

    def test_create_project_400s_with_invalid_user(self):
        project_data = self._create_project_data()
        project_data['project']['userId'] = 9999999

        res = self.client.post('/direct-award/projects', data=json.dumps(project_data), content_type='application/json')
        assert res.status_code == 400

    def test_create_project_creates_audit_event(self):
        res = self.client.post('/direct-award/projects', data=json.dumps(self._create_project_data()),
                               content_type='application/json')
        assert res.status_code == 201

        with self.app.app_context():
            assert len(AuditEvent.query.all()) == 1
            assert AuditEvent.query.all()[0].type == AuditTypes.create_project.value


class TestDirectAwardGetProject(DirectAwardSetupAndTeardown):
    def setup(self):
        super(TestDirectAwardGetProject, self).setup()
        self.project_id = self.create_direct_award_project(user_id=self.user_id,
                                                           project_name=self.direct_award_project_name)

        res = self.client.get('/direct-award/projects/{}?user-id={}'.format(self.project_id, self.user_id))
        assert res.status_code == 200

    def test_get_project_returns_serialized_project(self):
        res = self.client.get('/direct-award/projects/{}?user-id={}'.format(self.project_id, self.user_id))
        data = json.loads(res.get_data(as_text=True))

        with self.app.app_context():
            assert data['project'] == DirectAwardProject.query.get(self.project_id).serialize(with_users=True)


class TestDirectAwardListProjectSearches(DirectAwardSetupAndTeardown):
    def setup(self):
        super(TestDirectAwardListProjectSearches, self).setup()
        self.project_id = self.create_direct_award_project(user_id=self.user_id,
                                                           project_name=self.direct_award_project_name)
        self.search_id = self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id)

    def test_list_searches_200s_with_user_id(self):
        res = self.client.get('/direct-award/projects/{}/searches?user-id={}'.format(self.project_id,
                                                                                     self.user_id))
        assert res.status_code == 200

    def test_list_searches_returns_only_for_project_requested(self):
        # Create a project for another user with a search, i.e. one that shouldn't be returned
        self.setup_dummy_user(id=self.user_id + 1, role='buyer')
        self.create_direct_award_project(user_id=self.user_id + 1, project_id=self.project_id + 1)
        self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id + 1)

        res = self.client.get('/direct-award/projects/{}/searches'.format(self.project_id))
        data = json.loads(res.get_data(as_text=True))

        with self.app.app_context():
            assert all([search['projectId'] == self.project_id for search in data['searches']])
            assert data['meta']['total'] < len(DirectAwardSearch.query.all())

    def test_list_searches_returns_all_searches_for_project(self):
        self.search_id = self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id,
                                                                 active=False)

        res = self.client.get('/direct-award/projects/{}/searches?user-id={}'.format(self.project_id, self.user_id))
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['searches']) == 2

        with self.app.app_context():
            searches = DirectAwardSearch.query.filter(DirectAwardSearch.project_id == self.project_id)

            assert all([search.serialize() in data['searches'] for search in searches.all()])
            assert data['meta']['total'] == len(searches.all())

    @pytest.mark.parametrize('page_size, extra_searches',
                             ((1, 0),  # Page size == number of projects, shouldn't paginate
                              (2, 0),  # Page size > number of projects, shouldn't paginate
                              (2, 2),  # Page size < number of projects, should paginate (pages=2)
                              (2, 9),  # Page size < number of projects, should paginate (pages=5)
                              ))
    def test_list_searches_paginates_and_links_correctly(self, page_size, extra_searches):
        self.app.config['DM_API_PROJECTS_PAGE_SIZE'] = page_size

        for i in range(extra_searches):
            self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id, active=False)

        res = self.client.get('/direct-award/projects/{}/searches?user-id={}'.format(self.project_id, self.user_id))
        data = json.loads(res.get_data(as_text=True))

        num_pages = math.ceil((extra_searches + 1) / page_size)
        if num_pages > 1:
            assert data['links']['last'].endswith('&page={}'.format(num_pages))
            assert 'next' in data['links']

        else:
            assert 'last' not in data['links']
            assert 'next' not in data['links']

    def test_list_searches_accepts_page_offset(self):
        self.app.config['DM_API_PROJECTS_PAGE_SIZE'] = 2

        for i in range(10):
            self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id, active=False)

        data = {}
        searches_seen = []
        pages = 0
        while pages == 0 or data['links']['next'] != data['links']['last']:
            res = self.client.get('/direct-award/projects/{}/searches?user-id={}&page={}'.format(self.project_id,
                                                                                                 self.user_id,
                                                                                                 pages + 1))
            data = json.loads(res.get_data(as_text=True))

            for search in data['searches']:
                searches_seen.append(search['id'])

            pages += 1

        assert len(set(searches_seen)) == self.app.config['DM_API_PROJECTS_PAGE_SIZE'] * pages

    def test_list_searches_orders_by_id(self):
        self.app.config['DM_API_PROJECTS_PAGE_SIZE'] = 2

        for i in range(10):
            self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id, active=False,
                                                    created_at=datetime(2017, 1, 1, 0, 0, 0))

        last_seen = 0
        for i in range(5):
            res = self.client.get('/direct-award/projects/{}/searches?user-id={}&page={}'.format(self.project_id,
                                                                                                 self.user_id,
                                                                                                 i + 1))
            data = json.loads(res.get_data(as_text=True))

            # Check that each project has a created_at date older than the last, i.e. reverse chronological order.
            for search in data['searches']:
                assert last_seen < search['id']

    @pytest.mark.parametrize('only_active, expected_count, expected_states',
                             (
                                 (False, 2, [True, False]),
                                 (True, 1, [True])
                             ))
    def test_list_searches_respects_only_active_parameter_when_returning_searches(self, only_active, expected_count,
                                                                                  expected_states):
        # Create an extra search so that, unadultered, the endpoint will return two searches (one active, one not).
        self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id, active=False,
                                                created_at=datetime(2017, 1, 1, 0, 0, 0))

        res = self.client.get('/direct-award/projects/{}/searches?user-id={}&only-active={}'.format(self.project_id,
                                                                                                    self.user_id,
                                                                                                    only_active))
        data = json.loads(res.get_data(as_text=True))
        assert len(data['searches']) == expected_count
        assert list(map(lambda search: search['active'], data['searches'])) == expected_states

    def test_list_searches_orders_by_created_at_descending(self):
        self.app.config['DM_API_PROJECTS_PAGE_SIZE'] = 2

        # Randomly shuffled list of years for created_at timestamps
        created_at_years = [2016 - i for i in range(10)]
        random.shuffle(created_at_years)

        for i in range(10):
            self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id, active=False,
                                                    created_at=datetime(created_at_years.pop(), 1, 1, 0, 0, 0))

        last_seen_datetime = None
        for i in range(5):
            res = self.client.get('/direct-award/projects/{}/searches?user-id={}&page={}'
                                  '&latest-first=true'.format(self.project_id, self.user_id, i + 1))
            data = json.loads(res.get_data(as_text=True))

            # Check that each project has a created_at date older than the last, i.e. reverse chronological order.
            for search in data['searches']:
                next_datetime = datetime.strptime(search['createdAt'], DATETIME_FORMAT)

                if last_seen_datetime:
                    assert next_datetime < last_seen_datetime

                last_seen_datetime = next_datetime

    def test_list_searches_returns_serialized_searches_with_metadata(self):
        res = self.client.get('/direct-award/projects/{}/searches?user-id={}'.format(self.project_id,
                                                                                     self.user_id))
        data = json.loads(res.get_data(as_text=True))

        assert 'searches' in data
        assert data['meta']['total'] == 1
        assert len(data['searches']) == 1

        with self.app.app_context():
            assert data['searches'][0] == DirectAwardSearch.query.get(self.search_id).serialize()


class TestDirectAwardCreateProjectSearch(DirectAwardSetupAndTeardown):
    def _create_project_search_data(self):
        return {
            'search': {
                'userId': self.user_id,
                'searchUrl': self.direct_award_search_url,
            },
            'updated_by': str(self.user_id)
        }.copy()

    def setup(self):
        super(TestDirectAwardCreateProjectSearch, self).setup()
        self.project_id = self.create_direct_award_project(user_id=self.user_id,
                                                           project_name=self.direct_award_project_name)

    @pytest.mark.parametrize('drop_search_keys, expected_status',
                             (
                                 ([], 201),  # All required keys
                                 (['updated_by'], 400))  # Don't send updated_by
                             )
    def test_create_search_requires_updated_by(self, drop_search_keys, expected_status):
        search_data = self._create_project_search_data()
        for key in drop_search_keys:
            del search_data[key]

        res = self.client.post('/direct-award/projects/{}/searches'.format(self.project_id),
                               data=json.dumps(search_data),
                               content_type='application/json')
        assert res.status_code == expected_status

    @pytest.mark.parametrize('drop_search_keys, expected_status',
                             (
                                 ([], 201),  # All required keys
                                 (['userId'], 400),  # Don't send user_id
                                 (['searchUrl'], 400),  # Don't send project search_url
                                 (['userId', 'searchUrl'], 400))  # Don't send user_id or search_url
                             )
    def test_create_search_requires_search_key_with_url_and_user_id(self, drop_search_keys, expected_status):
        search_data = self._create_project_search_data()
        for key in drop_search_keys:
            del search_data['search'][key]

        res = self.client.post('/direct-award/projects/{}/searches'.format(self.project_id),
                               data=json.dumps(search_data),
                               content_type='application/json')
        assert res.status_code == expected_status

    def test_create_search_400s_with_invalid_user(self):
        search_data = self._create_project_search_data()
        search_data['search']['userId'] = 9999999

        res = self.client.post('/direct-award/projects/{}/searches'.format(self.project_id),
                               data=json.dumps(search_data), content_type='application/json')
        assert res.status_code == 400

    def test_create_search_makes_other_searches_inactive(self):
        search_data = self._create_project_search_data()

        res = self.client.post('/direct-award/projects/{}/searches'.format(self.project_id),
                               data=json.dumps(search_data), content_type='application/json')
        data = json.loads(res.get_data(as_text=True))
        first_search_id = data['search']['id']

        assert data['search']['active'] is True

        res = self.client.post('/direct-award/projects/{}/searches'.format(self.project_id),
                               data=json.dumps(search_data), content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert data['search']['active'] is True

        res = self.client.get('/direct-award/projects/{}/searches/{}?user-id={}'.format(self.project_id,
                                                                                        first_search_id,
                                                                                        self.user_id))
        data = json.loads(res.get_data(as_text=True))

        assert data['search']['active'] is False

    def test_create_project_creates_audit_event(self):
        res = self.client.post('/direct-award/projects/{}/searches'.format(self.project_id),
                               data=json.dumps(self._create_project_search_data()),
                               content_type='application/json')
        assert res.status_code == 201

        with self.app.app_context():
            assert len(AuditEvent.query.all()) == 1
            assert AuditEvent.query.all()[0].type == AuditTypes.create_project_search.value


class TestDirectAwardGetProjectSearch(DirectAwardSetupAndTeardown):
    def setup(self):
        super(TestDirectAwardGetProjectSearch, self).setup()
        self.project_id = self.create_direct_award_project(user_id=self.user_id,
                                                           project_name=self.direct_award_project_name)
        self.search_id = self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id)

        res = self.client.get('/direct-award/projects/{}/searches/{}?user-id={}'.format(self.project_id,
                                                                                        self.search_id,
                                                                                        self.user_id))
        assert res.status_code == 200

    def test_get_search_returns_serialized_search(self):
        res = self.client.get('/direct-award/projects/{}/searches/{}?user-id={}'.format(self.project_id,
                                                                                        self.search_id,
                                                                                        self.user_id))
        data = json.loads(res.get_data(as_text=True))

        with self.app.app_context():
            assert data['search'] == DirectAwardSearch.query.get(self.search_id).serialize()


class TestDirectAwardLockProject(DirectAwardSetupAndTeardown):
    def setup(self):
        super(TestDirectAwardLockProject, self).setup()
        self.project_id = self.create_direct_award_project(user_id=self.user_id,
                                                           project_name=self.direct_award_project_name)
        self.search_id = self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id)

        res = self.client.get('/direct-award/projects/{}/searches/{}?user-id={}'.format(self.project_id,
                                                                                        self.search_id,
                                                                                        self.user_id))
        assert res.status_code == 200

    def _lock_project_data(self):
        return {
            'updated_by': str(self.user_id)
        }.copy()

    @pytest.mark.skip
    def test_400s_if_project_already_locked(self):
        pass

    @pytest.mark.skip
    def test_search_and_project_datetimes_are_updated(self):
        pass

    @pytest.mark.skip
    def test_search_result_entries_populated_with_latest_archived_service_for_searched_services(self):
        pass

    @pytest.mark.skip
    def test_locking_project_creates_audit_event(self):
        pass
