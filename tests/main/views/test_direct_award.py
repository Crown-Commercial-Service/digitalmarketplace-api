import json
from datetime import datetime
from freezegun import freeze_time
import math
import random
import sys

import mock
from app import db

import pytest
from tests.bases import BaseApplicationTest

from sqlalchemy import desc, BigInteger
from dmapiclient.audit import AuditTypes

from app.models import DATETIME_FORMAT, AuditEvent, User, ArchivedService
from app.models.direct_award import (
    DirectAwardProjectUser,
    DirectAwardSearch,
    DirectAwardProject,
    DirectAwardSearchResultEntry
)
from ...helpers import (
    DIRECT_AWARD_SEARCH_URL, DIRECT_AWARD_PROJECT_NAME, DIRECT_AWARD_FROZEN_TIME, load_example_listing, FixtureMixin
)


class DirectAwardSetupAndTeardown(BaseApplicationTest, FixtureMixin):
    def setup(self):
        super(DirectAwardSetupAndTeardown, self).setup()
        self.user_id = self.setup_dummy_user(id=1, role='buyer')
        self.direct_award_project_name = DIRECT_AWARD_PROJECT_NAME
        self.direct_award_search_url = DIRECT_AWARD_SEARCH_URL

    def teardown(self):
        super(DirectAwardSetupAndTeardown, self).teardown()

    def _create_project_data(self):
        return {
            'project': {
                'userId': self.user_id,
                'name': self.direct_award_project_name,
            },
            'updated_by': str(self.user_id)
        }.copy()

    def _updated_by_data(self):
        return {'updated_by': str(self.user_id)}

    @staticmethod
    def _assert_one_audit_event_created_for_only_project(audit_type):
        projects = DirectAwardProject.query.all()
        assert len(projects) == 1

        audit_events = AuditEvent.query.filter(AuditEvent.type == audit_type,
                                               AuditEvent.data['projectExternalId'].astext.cast(BigInteger)
                                               == projects[0].external_id).all()
        assert len(audit_events) == 1


class TestDirectAwardListProjects(DirectAwardSetupAndTeardown):
    def setup(self):
        super(TestDirectAwardListProjects, self).setup()
        self.project_id, self.project_external_id = self.create_direct_award_project(
            user_id=self.user_id, project_name=self.direct_award_project_name
        )

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

    def test_list_projects_orders_by_internal_id(self):
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

            for project in data['projects']:
                project = DirectAwardProject.query.filter(DirectAwardProject.external_id == project['id']).first()
                assert last_seen < project.id
                last_seen = project.id

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

        assert data['projects'][0] == DirectAwardProject.query.get(self.project_id).serialize()

    def test_returns_serialized_project_with_users_if_requested(self):
        res = self.client.get('/direct-award/projects?include=users')
        data = json.loads(res.get_data(as_text=True))

        assert 'projects' in data
        assert data['meta']['total'] == 1
        assert len(data['projects']) == 1
        assert len(data['projects'][0]['users']) == 1

        assert data['projects'][0]['users'][0]['id'] == \
            DirectAwardProject.query.get(self.project_id).users[0].serialize()['id']

    @pytest.mark.parametrize('param', ('?include=no-users', ''))
    def test_returns_serialized_project_without_users_if_not_requested_correctly(self, param):
        res = self.client.get('/direct-award/projects{}'.format(param))
        data = json.loads(res.get_data(as_text=True))

        assert 'projects' in data
        assert data['meta']['total'] == 1
        assert len(data['projects']) == 1
        assert not data['projects'][0].get('users')


class TestDirectAwardCreateProject(DirectAwardSetupAndTeardown):
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

        assert len(DirectAwardProjectUser.query.all()) == 0

        res = self.client.post('/direct-award/projects', data=json.dumps(project_data), content_type='application/json')

        assert res.status_code == 201

        assert len(DirectAwardProjectUser.query.all()) == 1

    def test_create_project_retries_on_external_id_collision(self):
        project_data = self._create_project_data()

        assert len(DirectAwardProjectUser.query.all()) == 0

        with mock.patch('app.models.direct_award.DirectAwardProject.external_id.default.arg') as external_id_default:
            external_id_default.side_effect = (
                123456789012345,
                123456789012345,
                123456789012345,
                222222222222222,
            )

            res = self.client.post('/direct-award/projects', data=json.dumps(project_data),
                                   content_type='application/json')
            assert res.status_code == 201

            assert len(DirectAwardProjectUser.query.all()) == 1

    def test_create_project_fails_after_5_retries_on_external_id_collision(self):
        project_data = self._create_project_data()

        assert len(DirectAwardProjectUser.query.all()) == 0

        with mock.patch('app.models.direct_award.DirectAwardProject.external_id.default.arg') as external_id_default:
            external_id_default.side_effect = (
                123456789012345,
                123456789012345,
                123456789012345,
                123456789012345,
                123456789012345,
                123456789012345,
                123456789012345,
                222222222222222,
            )

            res = self.client.post('/direct-award/projects', data=json.dumps(project_data),
                                   content_type='application/json')
            assert res.status_code == 201

            res = self.client.post('/direct-award/projects', data=json.dumps(project_data),
                                   content_type='application/json')
            assert res.status_code == 400

    def test_create_project_400s_with_invalid_user(self):
        project_data = self._create_project_data()
        project_data['project']['userId'] = 9999999

        res = self.client.post('/direct-award/projects', data=json.dumps(project_data), content_type='application/json')
        assert res.status_code == 400

    def test_create_project_creates_audit_event(self):
        res = self.client.post('/direct-award/projects', data=json.dumps(self._create_project_data()),
                               content_type='application/json')
        assert res.status_code == 201

        self._assert_one_audit_event_created_for_only_project(AuditTypes.create_project.value)


class TestDirectAwardGetProject(DirectAwardSetupAndTeardown):
    def setup(self):
        super(TestDirectAwardGetProject, self).setup()
        self.project_id, self.project_external_id = self.create_direct_award_project(
            user_id=self.user_id, project_name=self.direct_award_project_name
        )

        res = self.client.get('/direct-award/projects/{}?user-id={}'.format(self.project_external_id, self.user_id))
        assert res.status_code == 200

    def test_get_project_returns_serialized_project(self):
        res = self.client.get('/direct-award/projects/{}?user-id={}'.format(self.project_external_id, self.user_id))
        data = json.loads(res.get_data(as_text=True))

        assert data['project'] == DirectAwardProject.query.get(self.project_id).serialize(with_users=True)


class TestDirectAwardListProjectSearches(DirectAwardSetupAndTeardown):
    def setup(self):
        super(TestDirectAwardListProjectSearches, self).setup()
        self.project_id, self.project_external_id = self.create_direct_award_project(
            user_id=self.user_id, project_name=self.direct_award_project_name
        )
        self.search_id = self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id)

    def test_list_searches_200s_with_user_id(self):
        res = self.client.get('/direct-award/projects/{}/searches?user-id={}'.format(self.project_external_id,
                                                                                     self.user_id))
        assert res.status_code == 200

    def test_list_searches_404s_with_invalid_project_id(self):
        res = self.client.get('/direct-award/projects/{}/searches?user-id={}'.format(sys.maxsize,
                                                                                     self.user_id))
        assert res.status_code == 404

    def test_list_searches_links_use_external_id(self):
        res = self.client.get('/direct-award/projects/{}/searches'.format(self.project_external_id))
        data = json.loads(res.get_data(as_text=True))

        assert data['links']['self'] == 'http://127.0.0.1:5000/direct-award/projects/{}/searches'.format(
            self.project_external_id
        )

    def test_list_searches_returns_only_for_project_requested(self):
        # Create a project for another user with a search, i.e. one that shouldn't be returned
        self.setup_dummy_user(id=self.user_id + 1, role='buyer')
        self.create_direct_award_project(user_id=self.user_id + 1, project_id=self.project_id + 1)
        self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id + 1)

        res = self.client.get('/direct-award/projects/{}/searches'.format(self.project_external_id))
        data = json.loads(res.get_data(as_text=True))

        assert all([search['projectId'] == self.project_external_id for search in data['searches']])
        assert data['meta']['total'] < len(DirectAwardSearch.query.all())

    def test_list_searches_returns_all_searches_for_project(self):
        self.search_id = self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id,
                                                                 active=False)

        res = self.client.get('/direct-award/projects/{}/searches?user-id={}'.format(self.project_external_id,
                                                                                     self.user_id))
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert len(data['searches']) == 2

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

        res = self.client.get('/direct-award/projects/{}/searches?user-id={}'.format(self.project_external_id,
                                                                                     self.user_id))
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
            res = self.client.get('/direct-award/projects/{}/searches?user-id={}&page={}'.format(
                self.project_external_id, self.user_id, pages + 1)
            )
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
            res = self.client.get('/direct-award/projects/{}/searches?user-id={}&page={}'.format(
                self.project_external_id, self.user_id, i + 1)
            )
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

        res = self.client.get('/direct-award/projects/{}/searches?user-id={}&only-active={}'.format(
            self.project_external_id, self.user_id, only_active)
        )
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
                                  '&latest-first=true'.format(self.project_external_id, self.user_id, i + 1))
            data = json.loads(res.get_data(as_text=True))

            # Check that each project has a created_at date older than the last, i.e. reverse chronological order.
            for search in data['searches']:
                next_datetime = datetime.strptime(search['createdAt'], DATETIME_FORMAT)

                if last_seen_datetime:
                    assert next_datetime < last_seen_datetime

                last_seen_datetime = next_datetime

    def test_list_searches_returns_serialized_searches_with_metadata(self):
        res = self.client.get('/direct-award/projects/{}/searches?user-id={}'.format(self.project_external_id,
                                                                                     self.user_id))
        data = json.loads(res.get_data(as_text=True))

        assert 'searches' in data
        assert data['meta']['total'] == 1
        assert len(data['searches']) == 1

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
        self.project_id, self.project_external_id = self.create_direct_award_project(
            user_id=self.user_id, project_name=self.direct_award_project_name
        )

    @pytest.mark.parametrize('drop_search_keys, expected_status',
                             (
                                 ([], 201),  # All required keys
                                 (['updated_by'], 400))  # Don't send updated_by
                             )
    def test_create_search_requires_updated_by(self, drop_search_keys, expected_status):
        search_data = self._create_project_search_data()
        for key in drop_search_keys:
            del search_data[key]

        res = self.client.post('/direct-award/projects/{}/searches'.format(self.project_external_id),
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

        res = self.client.post('/direct-award/projects/{}/searches'.format(self.project_external_id),
                               data=json.dumps(search_data),
                               content_type='application/json')
        assert res.status_code == expected_status

    def test_create_search_400s_with_invalid_user(self):
        search_data = self._create_project_search_data()
        search_data['search']['userId'] = 9999999

        res = self.client.post('/direct-award/projects/{}/searches'.format(self.project_external_id),
                               data=json.dumps(search_data), content_type='application/json')
        assert res.status_code == 400

    def test_create_search_404s_with_invalid_project(self):
        search_data = self._create_project_search_data()

        res = self.client.post('/direct-award/projects/{}/searches'.format(sys.maxsize),
                               data=json.dumps(search_data), content_type='application/json')
        assert res.status_code == 404

    def test_create_search_makes_other_searches_inactive(self):
        search_data = self._create_project_search_data()

        res = self.client.post('/direct-award/projects/{}/searches'.format(self.project_external_id),
                               data=json.dumps(search_data), content_type='application/json')
        data = json.loads(res.get_data(as_text=True))
        first_search_id = data['search']['id']

        assert data['search']['active'] is True

        res = self.client.post('/direct-award/projects/{}/searches'.format(self.project_external_id),
                               data=json.dumps(search_data), content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert data['search']['active'] is True

        res = self.client.get('/direct-award/projects/{}/searches/{}?user-id={}'.format(self.project_external_id,
                                                                                        first_search_id,
                                                                                        self.user_id))
        data = json.loads(res.get_data(as_text=True))

        assert data['search']['active'] is False

    def test_create_project_search_creates_audit_event(self):
        res = self.client.post('/direct-award/projects/{}/searches'.format(self.project_external_id),
                               data=json.dumps(self._create_project_search_data()),
                               content_type='application/json')
        assert res.status_code == 201

        self._assert_one_audit_event_created_for_only_project(AuditTypes.create_project_search.value)


class TestDirectAwardGetProjectSearch(DirectAwardSetupAndTeardown):
    def setup(self):
        super(TestDirectAwardGetProjectSearch, self).setup()
        self.project_id, self.project_external_id = self.create_direct_award_project(
            user_id=self.user_id, project_name=self.direct_award_project_name
        )
        self.search_id = self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id)

        res = self.client.get('/direct-award/projects/{}/searches/{}?user-id={}'.format(self.project_external_id,
                                                                                        self.search_id,
                                                                                        self.user_id))
        assert res.status_code == 200

    def test_get_search_404s_with_invalid_project(self):
        res = self.client.get('/direct-award/projects/{}/searches/{}?user-id={}'.format(sys.maxsize,
                                                                                        self.search_id,
                                                                                        self.user_id))
        assert res.status_code == 404

    def test_get_search_returns_serialized_search(self):
        res = self.client.get('/direct-award/projects/{}/searches/{}?user-id={}'.format(self.project_external_id,
                                                                                        self.search_id,
                                                                                        self.user_id))
        data = json.loads(res.get_data(as_text=True))

        assert data['search'] == DirectAwardSearch.query.get(self.search_id).serialize()


class TestDirectAwardListProjectServices(DirectAwardSetupAndTeardown):
    def setup(self):
        super(TestDirectAwardListProjectServices, self).setup()

        self.project_id, self.project_external_id = self.create_direct_award_project(
            user_id=self.user_id, project_name=self.direct_award_project_name
        )
        self.search_id = self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id)

        # Lock the project.
        project = DirectAwardProject.query.get(self.project_id)
        project.locked_at = datetime.utcnow()
        db.session.add(project)
        db.session.commit()

    def test_list_project_services_404s_on_invalid_project(self):
        res = self.client.get('/direct-award/projects/{}/services'.format(sys.maxsize))

        assert res.status_code == 404

    def test_list_project_services_400s_on_unlocked_project(self):
        # Unlock the project.
        project = DirectAwardProject.query.get(self.project_id)
        project.locked_at = None
        db.session.add(project)
        db.session.commit()

        res = self.client.get('/direct-award/projects/{}/services'.format(self.project_external_id))
        assert res.status_code == 400

    def test_list_project_services_400s_if_no_saved_search(self):
        # Delete the saved search so that none is assigned to the project.
        search = DirectAwardSearch.query.get(self.search_id)
        db.session.delete(search)
        db.session.commit()

        res = self.client.get('/direct-award/projects/{}/services'.format(self.project_external_id))

        assert res.status_code == 400

    def test_list_project_services_returns_correct_response(self):
        # Create some 'saved' services, which requires suppliers+archivedservice entries.
        self.setup_dummy_suppliers(3)
        self.setup_dummy_services(5, model=ArchivedService)

        archived_services = ArchivedService.query.all()
        for archived_service in archived_services:
            db.session.add(DirectAwardSearchResultEntry(archived_service_id=archived_service.id,
                                                        search_id=self.search_id))
        db.session.commit()
        expected_service_response = [{
            'id': service.service_id,
            'projectId': self.project_external_id,
            'supplier': {
                'name': service.supplier.name,
                'contact': {
                    'name': service.supplier.contact_information[0].contact_name,
                    'phone': service.supplier.contact_information[0].phone_number,
                    'email': service.supplier.contact_information[0].email,
                },
            },
            'data': {},
        } for service in archived_services]

        res = self.client.get('/direct-award/projects/{}/services'.format(self.project_external_id))
        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))

        assert set(data.keys()) == {'meta', 'links', 'services'}
        assert data['meta'] == {'total': 5}
        assert data['links'] == {'self': 'http://127.0.0.1:5000/direct-award/projects/{}/services'.format(
            self.project_external_id
        )}
        assert data['services'] == expected_service_response

    def test_list_project_services_returns_requested_fields_in_service_data(self):
        # Create some 'saved' services, which requires suppliers+archivedservice entries.
        self.setup_dummy_suppliers(1)
        self.setup_dummy_services(1, model=ArchivedService)

        archived_services = ArchivedService.query.all()
        for archived_service in archived_services:
            db.session.add(DirectAwardSearchResultEntry(archived_service_id=archived_service.id,
                                                        search_id=self.search_id))
        db.session.commit()
        service_name = archived_services[0].data['serviceName']

        res = self.client.get('/direct-award/projects/{}/services?fields=serviceName'.format(
            self.project_external_id)
        )
        assert res.status_code == 200

        data = json.loads(res.get_data(as_text=True))
        assert data['services'][0]['data'] == {'serviceName': service_name}
        assert data['links'] == {
            'self': 'http://127.0.0.1:5000/direct-award/projects/{}/services?fields=serviceName'.format(
                self.project_external_id
            )
        }

    def test_list_project_services_accepts_page_offset(self):
        project_services_count = 100

        # Create some 'saved' services, which requires suppliers+archivedservice entries.
        self.setup_dummy_suppliers(3)
        self.setup_dummy_services(project_services_count, model=ArchivedService)

        archived_services = ArchivedService.query.all()
        for archived_service in archived_services:
            db.session.add(DirectAwardSearchResultEntry(archived_service_id=archived_service.id,
                                                        search_id=self.search_id))
        db.session.commit()

        res = self.client.get('/direct-award/projects/{}/services?user-id={}'.format(self.project_external_id,
                                                                                     self.user_id))
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200

        assert len(data['services']) == self.app.config['DM_API_PROJECTS_PAGE_SIZE']
        assert data['meta']['total'] == project_services_count

        next_url = 'http://127.0.0.1:5000/direct-award/projects/{}/services?user-id={}&page=2'.format(
            self.project_external_id, self.user_id
        )
        last_url = 'http://127.0.0.1:5000/direct-award/projects/{}/services?user-id={}&page=20'.format(
            self.project_external_id, self.user_id
        )
        assert data['links']['next'] == next_url
        assert data['links']['last'] == last_url


class TestDirectAwardLockProject(DirectAwardSetupAndTeardown, FixtureMixin):
    def setup(self):
        super(TestDirectAwardLockProject, self).setup()
        self.project_id, self.project_external_id = self.create_direct_award_project(
            user_id=self.user_id, project_name=self.direct_award_project_name
        )
        self.search_id = self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id)

        res = self.client.get('/direct-award/projects/{}/searches/{}?user-id={}'.format(self.project_external_id,
                                                                                        self.search_id,
                                                                                        self.user_id))
        assert res.status_code == 200

    def _lock_project_data(self):
        return {
            'updated_by': str(self.user_id)
        }.copy()

    def test_lock_project_400s_if_project_already_locked(self):
        project = DirectAwardProject.query.get(self.project_id)
        project.locked_at = datetime.utcnow()

        db.session.add(project)
        db.session.commit()

        res = self.client.post(
            '/direct-award/projects/{}/lock'.format(self.project_external_id),
            data=json.dumps({
                'updated_by': 'example',
            }),
            content_type='application/json')

        assert res.status_code == 400

    def test_lock_project_404s_if_invalid_project(self):
        res = self.client.post(
            '/direct-award/projects/{}/lock'.format("not_a_valid_id"),
            data=json.dumps({
                'updated_by': 'example',
            }),
            content_type='application/json')

        assert res.status_code == 404

    @mock.patch('app.main.views.direct_award.search_api_client')
    def test_lock_project_success(self, search_api_client):
        self._create_service_and_update()
        service_id = "1234567890123458"
        search_api_client.search_services_from_url_iter.return_value = [{"id": service_id}]

        res = self.client.post(
            '/direct-award/projects/{}/lock'.format(self.project_external_id),
            data=json.dumps({
                'updated_by': 'example',
            }),
            content_type='application/json')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data['project']['id'] == self.project_external_id
        assert data['project']['lockedAt'] is not None

        assert AuditEvent.query.order_by(AuditEvent.id.desc()).first().type == AuditTypes.lock_project.value
        search_result_entry = DirectAwardSearchResultEntry.query.filter(
            DirectAwardSearchResultEntry.search_id == self.search_id
        )
        archived_services = ArchivedService.query.\
            filter(ArchivedService.service_id.in_([service_id])).\
            group_by(ArchivedService.id).\
            order_by(ArchivedService.service_id, desc(ArchivedService.id)).\
            distinct(ArchivedService.service_id).all()

        assert len(archived_services) > 0
        assert search_result_entry.count() == 1
        assert search_result_entry.all()[0].archived_service_id == archived_services[0].id

    def _create_service_and_update(self):
        with mock.patch('app.main.views.services.index_service'):
            service = load_example_listing("G6-SaaS")
            self.setup_dummy_suppliers(2)
            res1 = self.client.put(
                '/services/{}'.format(service['id']),
                data=json.dumps(
                    {
                        'updated_by': 'joeblogs',
                        'services': service
                    }
                ),
                content_type='application/json')

            assert res1.status_code == 201

            service['title'] = "New Service Title"
            service['createdAt'] = "2017-12-23T14:51:19Z"

            res2 = self.client.post(
                '/services/{}'.format(service['id']),
                data=json.dumps(
                    {
                        'updated_by': 'example',
                        'services': service
                    }
                ),
                content_type='application/json')

            assert res2.status_code == 200


class TestDirectAwardRecordProjectDownload(DirectAwardSetupAndTeardown):
    def setup(self):
        super(TestDirectAwardRecordProjectDownload, self).setup()
        self.project_id, self.project_external_id = self.create_direct_award_project(
            user_id=self.user_id, project_name=self.direct_award_project_name
        )
        self.search_id = self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id)

    @pytest.mark.parametrize('drop_project_keys, expected_status',
                             (
                                 ([], 200),  # All required keys
                                 (['updated_by'], 400))  # Don't send updated_by
                             )
    def test_record_project_download_requires_updated_by(self, drop_project_keys, expected_status):
        project_data = self._create_project_data()
        for key in drop_project_keys:
            del project_data[key]

        res = self.client.post('/direct-award/projects/{}/record-download'.format(self.project_external_id),
                               data=json.dumps(project_data),
                               content_type='application/json')
        assert res.status_code == expected_status

    @pytest.mark.parametrize('override_project_id, expected_status',
                             (
                                 (None, 200),
                                 (sys.maxsize, 404)
                             ))
    def test_record_project_download_404s_if_invalid_project(self, override_project_id, expected_status):
        if override_project_id:
            self.project_external_id = override_project_id

        res = self.client.post('/direct-award/projects/{}/record-download'.format(self.project_external_id),
                               data=json.dumps(self._updated_by_data()),
                               content_type='application/json')
        assert res.status_code == expected_status

    @freeze_time(DIRECT_AWARD_FROZEN_TIME)
    @pytest.mark.parametrize('downloaded_at, expected_timestamp',
                             (
                                 (None, DIRECT_AWARD_FROZEN_TIME),
                                 ('1990-01-01T00:00:00.000000Z', DIRECT_AWARD_FROZEN_TIME),
                             ))
    def test_record_project_download_timestamp_overrides_previous(self, downloaded_at, expected_timestamp):
        project = DirectAwardProject.query.get(self.project_id)
        project.downloaded_at = downloaded_at
        db.session.add(project)
        db.session.commit()

        self.client.post('/direct-award/projects/{}/record-download'.format(self.project_external_id),
                         data=json.dumps(self._updated_by_data()),
                         content_type='application/json')

        project = DirectAwardProject.query.get(self.project_id)
        assert project.downloaded_at == datetime.strptime(expected_timestamp, DATETIME_FORMAT)

    def test_record_project_download_creates_audit_event(self):
        res = self.client.post('/direct-award/projects/{}/record-download'.format(self.project_external_id),
                               data=json.dumps(self._updated_by_data()),
                               content_type='application/json')
        assert res.status_code == 200

        self._assert_one_audit_event_created_for_only_project(AuditTypes.downloaded_project.value)
