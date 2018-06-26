import json
from datetime import datetime
from freezegun import freeze_time
from itertools import chain, product
import math
import random
import re
import sys
from urllib.parse import urljoin

import mock
from app import db

import pytest
from tests.bases import BaseApplicationTest

from sqlalchemy import desc, BigInteger
from dmapiclient.audit import AuditTypes
from dmtestutils.comparisons import RestrictedAny, AnyStringMatching, AnySupersetOf

from app.models import DATETIME_FORMAT, AuditEvent, User, ArchivedService, Outcome
from app.models.direct_award import (
    DirectAwardProjectUser,
    DirectAwardSearch,
    DirectAwardProject,
    DirectAwardSearchResultEntry
)
from ...helpers import (
    DIRECT_AWARD_SEARCH_URL, DIRECT_AWARD_PROJECT_NAME, DIRECT_AWARD_FROZEN_TIME, load_example_listing, FixtureMixin
)


_anydict = AnySupersetOf({})


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
        assert res.status_code == 200

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
            assert res.status_code == 200

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
            assert res.status_code == 200

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
            assert res.status_code == 200

            # Check that each project has a created_at date older than the last, i.e. reverse chronological order.
            for project in data['projects']:
                next_datetime = datetime.strptime(project['createdAt'], DATETIME_FORMAT)

                if last_seen_datetime:
                    assert next_datetime < last_seen_datetime

                last_seen_datetime = next_datetime

    def test_list_projects_returns_serialized_project_with_metadata(self):
        res = self.client.get('/direct-award/projects?user-id={}'.format(self.user_id))
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert 'projects' in data
        assert data['meta']['total'] == 1
        assert len(data['projects']) == 1

        assert data['projects'][0] == DirectAwardProject.query.get(self.project_id).serialize()

    def test_returns_serialized_project_with_users_if_requested(self):
        res = self.client.get('/direct-award/projects?include=users')
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
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

        assert res.status_code == 200
        assert 'projects' in data
        assert data['meta']['total'] == 1
        assert len(data['projects']) == 1
        assert not data['projects'][0].get('users')

    def _create_projects_with_outcomes(self):
        self.project_incomplete_id, self.project_incomplete_external_id = self.create_direct_award_project(
            user_id=self.user_id,
            project_id=self.project_id + 1,
        )
        self.outcome_incomplete = Outcome(
            result="cancelled",
            direct_award_project_id=self.project_id + 1,
            completed_at=None,
        )
        db.session.add(self.outcome_incomplete)
        self.project_complete_id, self.project_complete_external_id = self.create_direct_award_project(
            user_id=self.user_id,
            project_id=self.project_id + 2,
        )
        self.outcome_complete = Outcome(
            result="none-suitable",
            direct_award_project_id=self.project_id + 2,
            completed_at=datetime(2018, 5, 4, 3, 2, 1),
        )
        db.session.add(self.outcome_complete)
        db.session.commit()

    def test_serialization_includes_completed_outcomes(self):
        self._create_projects_with_outcomes()

        res = self.client.get("/direct-award/projects")
        data = json.loads(res.get_data(as_text=True))

        db.session.add(self.outcome_complete)
        db.session.expire_all()

        assert res.status_code == 200
        assert data == AnySupersetOf({
            "projects": [
                AnySupersetOf({
                    "id": self.project_external_id,
                    "outcome": None,
                }),
                AnySupersetOf({
                    "id": self.project_incomplete_external_id,
                    "outcome": None,
                }),
                AnySupersetOf({
                    "id": self.project_complete_external_id,
                    "outcome": AnySupersetOf({
                        "id": self.outcome_complete.external_id,
                        "result": "none-suitable",
                        "completed": True,
                        "completedAt": "2018-05-04T03:02:01.000000Z",
                    }),
                }),
            ],
        })

    def test_filtering_having_outcome(self):
        self._create_projects_with_outcomes()

        res = self.client.get("/direct-award/projects?having-outcome=true")
        data = json.loads(res.get_data(as_text=True))

        db.session.add(self.outcome_complete)
        db.session.expire_all()

        assert res.status_code == 200
        assert data == AnySupersetOf({
            "projects": [
                AnySupersetOf({
                    "id": self.project_complete_external_id,
                    "outcome": AnySupersetOf({"id": self.outcome_complete.external_id}),
                }),
            ],
            "meta": AnySupersetOf({
                "total": 1,
            }),
        })

    def test_filtering_having_no_outcome(self):
        self._create_projects_with_outcomes()

        res = self.client.get("/direct-award/projects?having-outcome=false")
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data == AnySupersetOf({
            "projects": [
                AnySupersetOf({
                    "id": self.project_external_id,
                    "outcome": None,
                }),
                AnySupersetOf({
                    "id": self.project_incomplete_external_id,
                    "outcome": None,
                }),
            ],
            "meta": AnySupersetOf({
                "total": 2,
            }),
        })

    @pytest.mark.parametrize("set_locked", (False, True,))
    @pytest.mark.parametrize("filter_locked", (False, True,))
    def test_filtering_locked(self, set_locked, filter_locked):
        self.search_id = self.create_direct_award_project_search(created_by=self.user_id, project_id=self.project_id)

        locked_at_isoformat = None
        if set_locked:
            # Lock the project.
            project = DirectAwardProject.query.get(self.project_id)
            project.locked_at = datetime.utcnow()
            locked_at_isoformat = project.locked_at.isoformat()
            db.session.add(project)
            db.session.commit()

        res = self.client.get(f"/direct-award/projects?locked={filter_locked}")
        data = json.loads(res.get_data(as_text=True))

        assert res.status_code == 200
        assert data == AnySupersetOf({
            "projects": [
                AnySupersetOf({
                    "id": self.project_external_id,
                    "lockedAt": locked_at_isoformat and (locked_at_isoformat + "Z"),
                }),
            ] if set_locked == filter_locked else [],
            "meta": AnySupersetOf({
                "total": 1 if set_locked == filter_locked else 0,
            }),
        })


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


class TestDirectAwardOutcomeAward(DirectAwardSetupAndTeardown):
    def test_nonexistent_project_id(self):
        res = self.client.post(
            f"/direct-award/projects/976149527383380/services/2000000001/award",
            data=json.dumps(self._updated_by_data()),
            content_type="application/json",
        )
        assert res.status_code == 404
        assert json.loads(res.get_data()) == {
            "error": "Project 976149527383380 not found",
        }

    @pytest.mark.parametrize(
        (
            "has_active_search",
            "has_non_active_search",
            "active_search_has_chosen_sid",
            "non_active_search_has_chosen_sid",
            "project_locked",
            "existing_outcome_result",
            "existing_outcome_complete",
            "expected_status_code",
            "expected_response_data",
        ),
        (
            # "happy" paths
            (True, True, True, True, True, None, False, 200, _anydict,),
            (True, False, True, False, True, None, False, 200, _anydict,),
            (True, False, True, False, True, "awarded", False, 200, _anydict,),
            (True, True, True, False, True, "cancelled", False, 200, _anydict,),
            # "failure" paths
            (
                True,
                True,
                False,
                True,
                True,
                None,
                False,
                404,
                {
                    "error": AnyStringMatching(r"Service \d+ is not in project \d+\'s active search search results"),
                },
            ),
            (
                False,
                True,
                False,
                True,
                True,
                None,
                False,
                404,
                {
                    "error": AnyStringMatching(r"Project \d+ doesn't have an active search"),
                },
            ),
            (
                True,
                False,
                True,
                False,
                False,
                None,
                False,
                400,
                {
                    "error": AnyStringMatching(r"Project \d+ has not been locked"),
                },
            ),
            (
                True,
                False,
                False,
                False,
                False,
                None,
                False,
                400,
                {
                    "error": AnyStringMatching(r"Project \d+ has not been locked"),
                },
            ),
            (
                True,
                True,
                False,
                False,
                True,
                "cancelled",
                True,
                410,
                {
                    "error": AnyStringMatching(r"Project \d+ already has a completed outcome: \d+"),
                },
            ),
            (
                True,
                False,
                True,
                False,
                True,
                "awarded",
                True,
                410,
                {
                    "error": AnyStringMatching(r"Project \d+ already has a completed outcome: \d+"),
                },
            ),
        ),
        # help pytest make its printed representation of the parameter set a little more readable
        ids=(lambda val: "ANYDICT" if val is _anydict else None),
    )
    def test_direct_award_outcome_scenarios(
        self,
        has_active_search,
        has_non_active_search,
        active_search_has_chosen_sid,
        non_active_search_has_chosen_sid,
        project_locked,
        existing_outcome_result,
        existing_outcome_complete,
        expected_status_code,
        expected_response_data,
    ):
        """
        A number of arguments control the background context this test is run in. Clearly, not all of the combinations
        make sense together and a caller should not expect a test to pass with a nonsensical combination of arguments

        :param has_active_search:                 whether the project should have an active search
        :param has_non_active_search:             whether the project should have a non-active search
        :param active_search_has_chosen_sid:      whether the service_id we're going to "choose" should exist in the
                                                  active search
        :param non_active_search_has_chosen_sid:  whether the service_id we're going to "choose" should exist in the
                                                  non-active search
        :param project_locked:                    whether the project should be marked as "locked"
        :param existing_outcome_result:           what the "result" field of an existing Outcome for this project
                                                  should be set to, None for no existing Outcome
        :param existing_outcome_complete:         whether any existing existing Outcome for this project should
                                                  be marked as "complete"
        :param expected_status_code:              numeric status code to expect for this request
        :param expected_response_data:
        """
        self.setup_dummy_suppliers(3)
        self.setup_dummy_services(3, model=ArchivedService)

        project = DirectAwardProject(
            name=self.direct_award_project_name,
            users=[User.query.get(self.user_id)],
        )
        db.session.add(project)

        active_search = None
        if has_active_search:
            active_search = DirectAwardSearch(
                project=project,
                created_by=self.user_id,
                active=True,
                search_url="http://nothing.nowhere",
            )
            db.session.add(active_search)

        non_active_search = None
        if has_non_active_search:
            non_active_search = DirectAwardSearch(
                project=project,
                created_by=self.user_id,
                active=False,
                search_url="http://nothing.anyhere",
            )
            db.session.add(non_active_search)

        archived_service_non_chosen, archived_service_chosen = db.session.query(ArchivedService).filter(
            ArchivedService.service_id.in_(("2000000000", "2000000001",))
        ).order_by(ArchivedService.service_id).all()

        if active_search:
            active_search.archived_services.append(archived_service_non_chosen)
            if active_search_has_chosen_sid:
                active_search.archived_services.append(archived_service_chosen)
        if non_active_search:
            non_active_search.archived_services.append(archived_service_non_chosen)
            if non_active_search_has_chosen_sid:
                non_active_search.archived_services.append(archived_service_chosen)

        existing_outcome = None
        if existing_outcome_result is not None:
            # create an "existing" Outcome pointing at this project
            existing_outcome = Outcome(
                result=existing_outcome_result,
                direct_award_project=project,
                # if this test iteration wants an *awarded* existing_outcome we'll just set it to be awarded to
                # whichever service makes sense...
                **({
                    "direct_award_search": project.active_search,
                    "direct_award_archived_service": project.active_search.archived_services.order_by(
                        desc(ArchivedService.service_id)
                    ).first(),
                    "start_date": datetime(2020, 3, 3).date(),
                    "end_date": datetime(2020, 3, 3).date(),
                    "awarding_organisation_name": "Circumlocution department",
                    "award_value": 123,
                } if existing_outcome_result == "awarded" else {})
            )
            if existing_outcome_complete:
                # this has to be set *after* we know all the other fields are set due to the way sa's validators work
                existing_outcome.completed_at = datetime(2018, 2, 2, 2, 2, 2)
            db.session.add(existing_outcome)

        # must assign ids before we can lock project
        db.session.flush()
        if project_locked:
            project.locked_at = datetime.now()

        project_external_id = project.external_id
        active_search_id = active_search and active_search.id
        audit_event_count = AuditEvent.query.count()
        outcome_count = Outcome.query.count()
        chosen_archived_service_id = db.session.query(ArchivedService.id).filter_by(service_id="2000000001").first()[0]
        outcome_count = Outcome.query.count()
        db.session.commit()

        res = self.client.post(
            f"/direct-award/projects/{project.external_id}/services/2000000001/award",
            data=json.dumps(self._updated_by_data()),
            content_type="application/json",
        )
        assert res.status_code == expected_status_code
        response_data = json.loads(res.get_data())

        assert response_data == expected_response_data

        # allow these to be re-used in this session, "refreshed"
        db.session.add(project)
        if active_search:
            db.session.add(active_search)
        db.session.expire_all()

        if res.status_code != 200:
            # assert no database objects have been created
            assert Outcome.query.count() == outcome_count
            assert AuditEvent.query.count() == audit_event_count
        else:
            assert response_data == {
                "outcome": {
                    "id": RestrictedAny(lambda x: isinstance(x, int) and x > 0),
                    "result": "awarded",
                    "completed": False,
                    "completedAt": None,
                    "award": {
                        "awardValue": None,
                        "awardingOrganisationName": None,
                        "endDate": None,
                        "startDate": None,
                    },
                    "resultOfDirectAward": {
                        "project": {
                            "id": project_external_id,
                        },
                        "search": {
                            "id": active_search_id,
                        },
                        "archivedService": {
                            "id": chosen_archived_service_id,
                            "service": {
                                "id": "2000000001",
                            },
                        },
                    },
                }
            }

            # only one outcome has been created
            assert Outcome.query.count() == outcome_count + 1

            outcome = db.session.query(Outcome).filter_by(
                external_id=response_data["outcome"]["id"]
            ).first()

            # check the modifications actually hit the database correctly
            assert outcome.direct_award_project is project
            assert outcome.direct_award_project.active_search is active_search
            assert outcome.direct_award_search is active_search
            assert outcome.direct_award_archived_service.id == chosen_archived_service_id
            assert outcome.direct_award_archived_service.service_id == "2000000001"
            assert outcome.result == "awarded"
            assert outcome.completed_at is None
            assert outcome.start_date is outcome.end_date \
                is outcome.awarding_organisation_name is outcome.award_value is None

            assert AuditEvent.query.count() == audit_event_count + 1
            audit_event = db.session.query(AuditEvent).order_by(
                desc(AuditEvent.created_at),
                desc(AuditEvent.id),
            ).first()
            assert audit_event.object is outcome
            assert audit_event.acknowledged is False
            assert audit_event.acknowledged_at is None
            assert not audit_event.acknowledged_by
            assert audit_event.type == "create_outcome"
            assert audit_event.user == "1"
            assert audit_event.data == {
                "archivedServiceId": response_data["outcome"]["resultOfDirectAward"]["archivedService"]["id"],
                "projectExternalId": project_external_id,
                "searchId": active_search_id,
                "result": "awarded",
            }


class TestDirectAwardOutcomeNonAwarded(DirectAwardSetupAndTeardown):
    @pytest.mark.parametrize(
        "endpoint_rel_path",
        ("cancel", "none-suitable",)
    )
    def test_nonexistent_project_id(self, endpoint_rel_path):
        res = self.client.post(
            urljoin("/direct-award/projects/952738338097614/", endpoint_rel_path),
            data=json.dumps(self._updated_by_data()),
            content_type="application/json",
        )
        assert res.status_code == 404
        assert json.loads(res.get_data()) == {
            "error": "Project 952738338097614 not found",
        }

    # tuples of paramaters in the order:
    #     has_active_search
    #     has_non_active_search
    #     project_locked
    #     existing_outcome_result
    #     existing_outcome_complete
    #     expected_status_code
    #     expected_response_data
    _base_direct_award_nonawarded_scenarios = (
        # "happy" paths
        (True, True, True, None, False, 200, _anydict,),
        (True, False, True, None, False, 200, _anydict,),
        (False, True, True, "cancelled", False, 200, _anydict,),
        (True, False, True, "awarded", False, 200, _anydict,),
        (True, True, True, "cancelled", False, 200, _anydict,),
        (True, False, False, "none-suitable", False, 200, _anydict),
        (False, False, False, None, False, 200, _anydict),
        # "failure" paths
        (
            True,
            True,
            True,
            "cancelled",
            True,
            410,
            {
                "error": AnyStringMatching(r"Project \d+ already has a completed outcome: \d+"),
            },
        ),
        (
            True,
            False,
            True,
            "awarded",
            True,
            410,
            {
                "error": AnyStringMatching(r"Project \d+ already has a completed outcome: \d+"),
            },
        ),
    )

    @pytest.mark.parametrize(
        (
            "endpoint_rel_path",
            "has_active_search",
            "has_non_active_search",
            "project_locked",
            "existing_outcome_result",
            "existing_outcome_complete",
            "expected_status_code",
            "expected_response_data",
        ),
        tuple(chain(
            (
                # we test all of the _base_direct_award_nonawarded_scenarios against the known valid nonawarded reasons
                (endpoint_rel_path,) + base_scenario
                for endpoint_rel_path, base_scenario in product(
                    ("none-suitable", "cancel",),
                    _base_direct_award_nonawarded_scenarios,
                )
            ),
            (
                # but we also include a couple of specific cases with invalid reasons to make sure there isn't a view
                # taking the path component as an arbitrary reason
                (
                    "severe-chill",
                    True,
                    False,
                    True,
                    None,
                    False,
                    404,
                    {
                        "error": AnyStringMatching(r".*the requested url was not found.*", re.I),
                    },
                ),
                # Check that `awarded` is not a URI because awarding is done against a project URI
                (
                    "awarded",
                    True,
                    False,
                    True,
                    "awarded",
                    True,
                    404,
                    {
                        "error": AnyStringMatching(r".*the requested url was not found.*", re.I),
                    },
                ),
            ),
        )),
        # help pytest make its printed representation of the parameter set a little more readable
        ids=(lambda val: "ANYDICT" if val is _anydict else None),
    )
    def test_direct_award_nonawarded_scenarios(
        self,
        endpoint_rel_path,
        has_active_search,
        has_non_active_search,
        project_locked,
        existing_outcome_result,
        existing_outcome_complete,
        expected_status_code,
        expected_response_data,
    ):
        """
        A number of arguments control the background context this test is run in. Clearly, not all of the combinations
        make sense together and a caller should not expect a test to pass with a nonsensical combination of arguments

        :param endpoint_rel_path:         url path of endpoint to post to, relative to /direct-award/projects/<id>/
        :param has_active_search:         whether the project should have an active search
        :param has_non_active_search:     whether the project should have a non-active search
        :param project_locked:            whether the project should be marked as "locked"
        :param existing_outcome_result:   what the "result" field of an existing Outcome for this project should be set
                                          to, None for no existing Outcome
        :param existing_outcome_complete: whether any existing existing Outcome for this project should be marked as
                                          "complete"
        :param expected_status_code:      numeric status code to expect for this request
        :param expected_response_data:
        """
        if has_active_search or has_non_active_search or existing_outcome_result == "awarded":
            self.setup_dummy_suppliers(3)
            self.setup_dummy_services(3, model=ArchivedService)

        project = DirectAwardProject(
            name=self.direct_award_project_name,
            users=[User.query.get(self.user_id)],
        )
        db.session.add(project)

        active_search = None
        if has_active_search:
            active_search = DirectAwardSearch(
                project=project,
                created_by=self.user_id,
                active=True,
                search_url="http://nothing.nowhere",
            )
            db.session.add(active_search)

        non_active_search = None
        if has_non_active_search:
            non_active_search = DirectAwardSearch(
                project=project,
                created_by=self.user_id,
                active=False,
                search_url="http://nothing.anyhere",
            )
            db.session.add(non_active_search)

        archived_services = db.session.query(ArchivedService).filter(
            ArchivedService.service_id.in_(("2000000000", "2000000001",))
        ).order_by(ArchivedService.service_id).all()

        if active_search:
            # there really doesn't appear to be an append_all-like method for dynamic relationships
            for archived_service in archived_services:
                active_search.archived_services.append(archived_service)
        if non_active_search:
            for archived_service in archived_services:
                non_active_search.archived_services.append(archived_service)

        existing_outcome = None
        if existing_outcome_result is not None:
            # create an "existing" Outcome pointing at this project
            existing_outcome = Outcome(
                result=existing_outcome_result,
                direct_award_project=project,
                # if this test iteration wants an *awarded* existing_outcome we'll just set it to be awarded to
                # whichever service makes sense...
                **({
                    "direct_award_search": project.active_search,
                    "direct_award_archived_service": project.active_search.archived_services.order_by(
                        desc(ArchivedService.service_id)
                    ).first(),
                    "start_date": datetime(2002, 3, 30).date(),
                    "end_date": datetime(2002, 3, 30).date(),
                    "awarding_organisation_name": "Biscuit section",
                    "award_value": 321,
                } if existing_outcome_result == "awarded" else {})
            )
            if existing_outcome_complete:
                # this has to be set *after* we know all the other fields are set due to the way sa's validators work
                existing_outcome.completed_at = datetime(2018, 2, 2, 2, 2, 2)
            db.session.add(existing_outcome)

        # must assign ids before we can lock project
        db.session.flush()
        if project_locked:
            project.locked_at = datetime.now()

        project_external_id = project.external_id
        audit_event_count = AuditEvent.query.count()
        outcome_count = Outcome.query.count()
        db.session.commit()

        res = self.client.post(
            urljoin(f"/direct-award/projects/{project.external_id}/", endpoint_rel_path),
            data=json.dumps(self._updated_by_data()),
            content_type="application/json",
        )
        assert res.status_code == expected_status_code
        response_data = json.loads(res.get_data())

        assert response_data == expected_response_data

        # allow these to be re-used in this session, "refreshed"
        db.session.add(project)
        if active_search:
            db.session.add(active_search)
        db.session.expire_all()

        if res.status_code != 200:
            # also assert no database objects have been created
            assert Outcome.query.count() == outcome_count
            assert AuditEvent.query.count() == audit_event_count
        else:
            assert response_data == {
                "outcome": {
                    "id": RestrictedAny(lambda x: isinstance(x, int) and x > 0),
                    "result": {
                        "cancel": "cancelled",
                        "none-suitable": "none-suitable",
                    }[endpoint_rel_path],
                    "completed": True,
                    "completedAt": AnyStringMatching(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z"),
                    "resultOfDirectAward": {
                        "project": {
                            "id": project_external_id,
                        },
                    },
                }
            }

            # only one outcome has been created
            assert Outcome.query.count() == outcome_count + 1

            outcome = db.session.query(Outcome).filter_by(
                external_id=response_data["outcome"]["id"]
            ).first()

            # check the modifications actually hit the database correctly
            assert outcome.direct_award_project is project
            assert outcome.direct_award_search is None
            assert outcome.direct_award_archived_service is None
            assert outcome.completed_at is not None
            assert outcome.start_date is outcome.end_date \
                is outcome.awarding_organisation_name is outcome.award_value is None

            # of course it should serialize back to the received output
            assert response_data == {
                "outcome": outcome.serialize(),
            }

            assert AuditEvent.query.count() == audit_event_count + 2
            # grab those most recent 2 audit events from the db, re-sorting them to be in a predictable order -
            # we don't care whether the complete_outcome or update_outcome comes out of the db first
            audit_events = sorted(
                db.session.query(AuditEvent).order_by(
                    desc(AuditEvent.created_at),
                    desc(AuditEvent.id),
                )[:2],
                key=lambda ae: ae.type,
            )

            assert audit_events[0].type == "complete_outcome"
            assert audit_events[0].created_at == audit_events[1].created_at == outcome.completed_at
            assert audit_events[0].object is outcome
            assert audit_events[0].acknowledged is False
            assert audit_events[0].acknowledged_at is None
            assert not audit_events[0].acknowledged_by
            assert audit_events[0].user == "1"
            assert audit_events[0].data == {}

            assert audit_events[1].object is outcome
            assert audit_events[1].acknowledged is False
            assert audit_events[1].acknowledged_at is None
            assert not audit_events[1].acknowledged_by
            assert audit_events[1].type == "create_outcome"
            assert audit_events[1].user == "1"
            assert audit_events[1].data == {
                "projectExternalId": project_external_id,
                "result": {
                    "cancel": "cancelled",
                    "none-suitable": "none-suitable",
                }[endpoint_rel_path],
            }
