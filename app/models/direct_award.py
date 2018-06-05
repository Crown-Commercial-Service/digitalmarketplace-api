from datetime import datetime
from urllib.parse import urljoin

from sqlalchemy.orm import validates
from flask import current_app

from app import db
from app.utils import random_positive_external_id
from app.url_utils import force_relative_url
from app.models import User, ValidationError, ArchivedService

from dmutils.formats import DATETIME_FORMAT


class DirectAwardProject(db.Model):
    __tablename__ = 'direct_award_projects'

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.BigInteger, default=random_positive_external_id, nullable=False, index=True, unique=True)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    locked_at = db.Column(db.DateTime, nullable=True)  # When the project's active search/es are final and cannot change
    downloaded_at = db.Column(db.DateTime, nullable=True)  # When the project's shortlist was last downloaded
    active = db.Column(db.Boolean, default=True, nullable=False)

    users = db.relationship(User, secondary='direct_award_project_users', order_by=lambda: DirectAwardProjectUser.id)

    def serialize(self, with_users=False):
        data = {
            "id": self.external_id,
            "name": self.name,
            "createdAt": self.created_at.strftime(DATETIME_FORMAT),
            "lockedAt": self.locked_at.strftime(DATETIME_FORMAT) if self.locked_at is not None else None,
            "downloadedAt": self.downloaded_at.strftime(DATETIME_FORMAT) if self.downloaded_at is not None else None,
            "active": self.active
        }

        if with_users:
            data['users'] = [
                {k: v for k, v in user.serialize().items() if k in {'active', 'emailAddress', 'id', 'name', 'role'}}
                for user in self.users
            ]

        return data

    @validates('name')
    def _assert_active_project(self, key, value):
        if self.locked_at:
            raise ValidationError('Cannot change project name after locking it ({})'.format(self.id))

        return value


class DirectAwardProjectUser(db.Model):
    __tablename__ = 'direct_award_project_users'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('direct_award_projects.id'), index=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True, nullable=False)


class DirectAwardSearch(db.Model):
    __tablename__ = 'direct_award_searches'

    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('direct_award_projects.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # When this search was first saved.
    searched_at = db.Column(db.DateTime, nullable=True)  # When this search was run for the project services download.
    search_url = db.Column(db.Text, nullable=False)  # Search API URL to hit when retrieving services.
    active = db.Column(db.Boolean, default=True, nullable=False, index=True)  # Is the 'current' search for the project

    # Access archived_services relating to this search. Should only have related services after the project
    # has been downloaded, and this is the search for that project that was chosen as the search to longlist/shortlist
    # against.
    # Note: an archived service is not a service from an old framework, as one might think. An ArchivedService is
    # created when an attribute on a service is changed. By storing the ArchivedService id we are referencing a service
    # in a given state at a specific time. We can still access the live version of the service through the Archived
    # Service, but by storing this we have the flexibility to show either the live state or the state at the time
    # the user ran the search.
    archived_services = db.relationship(ArchivedService, secondary='direct_award_search_result_entries',
                                        order_by=lambda: DirectAwardSearchResultEntry.id, lazy='dynamic')

    project = db.relationship(DirectAwardProject)
    user = db.relationship(User)

    __table_args__ = (
        # this may appear tautological (id is a unique column *on its own*, so clearly the combination of id/project_id
        # is), but is required by postgres to be able to make a compound foreign key to these together
        db.UniqueConstraint(id, project_id, name="uq_direct_award_searches_id_project_id"),
        # Partial index on project_id,active==1. Enforces only one active search per project at a time.
        db.Index('idx_project_id_active', project_id, active, unique=True, postgresql_where=db.Column('active')),
    )

    def serialize(self):
        resolved_search_url = urljoin(current_app.config['DM_SEARCH_API_URL'], self.search_url)
        return {
            "id": self.id,
            "createdBy": self.created_by,
            "projectId": self.project.external_id,
            "createdAt": self.created_at.strftime(DATETIME_FORMAT),
            "searchedAt": self.searched_at.strftime(DATETIME_FORMAT) if self.searched_at is not None else None,
            "searchUrl": resolved_search_url,
            "active": self.active
        }

    @validates('id', 'created_by', 'project_id', 'created_at', 'searched_at', 'search_url', 'active')
    def _assert_active_project(self, key, value):
        if self.project and self.project.locked_at:
            raise ValidationError('Cannot change attributes of a search under a project ({}) that '
                                  'has been locked.'.format(self.project_id))
        if key == 'search_url' and value:
            # remove hostname etc so that stored URI is always relative to the base Search API URI in our config
            return force_relative_url(current_app.config['DM_SEARCH_API_URL'], value)

        else:
            return value


class DirectAwardSearchResultEntry(db.Model):
    __tablename__ = 'direct_award_search_result_entries'

    id = db.Column(db.Integer, primary_key=True)
    search_id = db.Column(db.Integer, db.ForeignKey('direct_award_searches.id'), index=True, nullable=False)
    archived_service_id = db.Column(db.Integer, db.ForeignKey('archived_services.id'), index=True, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            archived_service_id,
            search_id,
            name="uq_direct_award_search_result_entries_archived_service_id_search_id",
        ),
    )
