from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import User, ValidationError
from app.models.direct_award import Project, ProjectUser, Search
from tests.bases import BaseApplicationTest
from tests.helpers import FixtureMixin, DIRECT_AWARD_PROJECT_NAME, DIRECT_AWARD_SEARCH_URL


class TestProjects(BaseApplicationTest, FixtureMixin):
    def test_create_new_project(self):
        with self.app.app_context():
            self.setup_dummy_user(role='buyer')

            project = Project(name=DIRECT_AWARD_PROJECT_NAME, users=User.query.all())
            db.session.add(project)
            db.session.commit()

            assert project.id is not None
            assert project.name == DIRECT_AWARD_PROJECT_NAME
            assert isinstance(project.created_at, datetime)
            assert project.locked_at is None
            assert project.active is True

    def test_serialize_project_contains_required_keys(self):
        with self.app.app_context():
            self.setup_dummy_user(role='buyer')

            project = Project(name=DIRECT_AWARD_PROJECT_NAME, users=User.query.all())
            db.session.add(project)
            db.session.commit()

            project_keys_set = set(project.serialize().keys())
            assert {'id', 'name', 'createdAt', 'lockedAt', 'active'} <= project_keys_set

    def test_create_new_project_creates_project_users(self):
        with self.app.app_context():
            self.setup_dummy_user(role='buyer')

            assert len(ProjectUser.query.all()) == 0

            project = Project(name=DIRECT_AWARD_PROJECT_NAME, users=User.query.all())
            db.session.add(project)
            db.session.commit()

            assert len(ProjectUser.query.all()) == len(User.query.all())


class TestProjectUsers(BaseApplicationTest, FixtureMixin):
    @pytest.mark.parametrize('create_project, create_user, expect_error',
                             (
                                 (False, False, True),
                                 (True, False, True),
                                 (False, True, True),
                                 (True, True, False)
                             ))
    def test_project_user_fk_constraints(self, create_project, create_user, expect_error):
        with self.app.app_context():
            if create_project:
                project = Project(id=1, name=DIRECT_AWARD_PROJECT_NAME, users=[])
                db.session.add(project)
                db.session.commit()

            if create_user:
                self.setup_dummy_user(role='buyer', id=2)

            project_user = ProjectUser(project_id=1, user_id=2)
            db.session.add(project_user)

            if expect_error:
                with pytest.raises(IntegrityError):
                    db.session.commit()
            else:
                db.session.commit()

                assert project_user.project_id == 1
                assert project_user.user_id == 2


class TestSearches(BaseApplicationTest, FixtureMixin):
    def test_create_new_search(self):
        user_id = self.setup_dummy_user(role='buyer')
        project_id = self.create_direct_award_project(user_id=user_id)
        search_id = self.create_direct_award_project_search(created_by=user_id, project_id=project_id)

        with self.app.app_context():
            search = Search.query.get(search_id)
            assert search.id == search_id
            assert search.project_id == project_id
            assert isinstance(search.created_at, datetime)
            assert search.searched_at is None
            assert search.search_url == DIRECT_AWARD_SEARCH_URL
            assert search.active is True

    def test_only_one_search_active_per_project_is_enforced(self):
        user_id = self.setup_dummy_user(role='buyer')
        project_id = self.create_direct_award_project(user_id=user_id)
        self.create_direct_award_project_search(created_by=user_id, project_id=project_id)

        with pytest.raises(IntegrityError):
            self.create_direct_award_project_search(created_by=user_id, project_id=project_id)

    def test_serialize_search_contains_required_keys(self):
        user_id = self.setup_dummy_user(role='buyer')
        project_id = self.create_direct_award_project(user_id=user_id)
        search_id = self.create_direct_award_project_search(created_by=user_id, project_id=project_id)

        with self.app.app_context():
            search = Search.query.get(search_id)

        search_keys_set = set(search.serialize().keys())
        assert {'id', 'createdAt', 'searchedAt', 'projectId', 'searchUrl', 'active'} <= search_keys_set

    @pytest.mark.parametrize('update_kwargs',
                             (
                                 {'project_id': None},
                                 {'search_url': None}
                             ))
    def test_required_fields_raise_if_missing(self, update_kwargs):
        user_id = self.setup_dummy_user(role='buyer')
        project_id = self.create_direct_award_project(user_id=user_id)

        search_kwargs = {'created_by': user_id, 'project_id': project_id, 'search_url': DIRECT_AWARD_SEARCH_URL}
        search_kwargs.update(update_kwargs)

        with pytest.raises(IntegrityError):
            self.create_direct_award_project_search(**search_kwargs)

    def test_search_in_locked_project_cannot_be_edited(self):
        user_id = self.setup_dummy_user(role='buyer')
        project_id = self.create_direct_award_project(user_id=user_id)
        search_id = self.create_direct_award_project_search(created_by=user_id, project_id=project_id)

        with self.app.app_context():
            search = Search.query.get(search_id)
            project = Project.query.get(project_id)
            project.locked_at = datetime.utcnow()
            db.session.add(project)
            db.session.commit()

            for prop in ['id', 'created_by', 'project_id', 'created_at', 'searched_at', 'search_url', 'active']:
                with pytest.raises(ValidationError):
                    setattr(search, prop, getattr(search, prop))


class TestProjectSearchResultEntries(BaseApplicationTest, FixtureMixin):
    @pytest.mark.parametrize('create_user, create_project, expect_error',
                             (
                                 (False, False, True),
                                 (True, False, True),
                                 (False, True, True),
                                 (True, True, False)
                             ))
    def test_search_result_entries_fk_constraints(self, create_user, create_project, expect_error):
        with self.app.app_context():
            if create_user:
                self.setup_dummy_user(role='buyer', id=1)

            if create_project:
                project = Project(id=1, name=DIRECT_AWARD_PROJECT_NAME, users=[])
                db.session.add(project)
                db.session.commit()

            project_user = ProjectUser(project_id=1, user_id=1)
            db.session.add(project_user)

            if expect_error:
                with pytest.raises(IntegrityError):
                    db.session.commit()
            else:
                db.session.commit()
