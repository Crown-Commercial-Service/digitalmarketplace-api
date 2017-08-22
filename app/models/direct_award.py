from datetime import datetime

from sqlalchemy.orm import validates

from app import db
from app.models import User, ValidationError, ArchivedService
from dmutils.formats import DATETIME_FORMAT


class Project(db.Model):
    __tablename__ = 'direct_award_projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    locked_at = db.Column(db.DateTime, nullable=True)  # When the project's active search/es are final and cannot change
    active = db.Column(db.Boolean, default=True, nullable=False)

    users = db.relationship(User, secondary='direct_award_project_users', order_by=lambda: ProjectUser.id)

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "createdAt": self.created_at.strftime(DATETIME_FORMAT),
            "lockedAt": self.locked_at.strftime(DATETIME_FORMAT) if self.locked_at is not None else None,
            "active": self.active
        }

    @validates('name')
    def _assert_active_project(self, key, value):
        if self.locked_at:
            raise ValidationError('Cannot change project name after locking it ({})'.format(self.id))

        return value


class ProjectUser(db.Model):
    __tablename__ = 'direct_award_project_users'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('direct_award_projects.id'), index=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True, nullable=False)


class Search(db.Model):
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
                                        order_by=lambda: SearchResultEntry.id)

    project = db.relationship(Project)
    user = db.relationship(User)

    # Partial index on project_id,active==1. Enforces only one active search per project at a time.
    __table_args__ = (db.Index('idx_project_id_active', project_id, active, unique=True,
                               postgresql_where=db.Column('active')),)

    def serialize(self):
        return {
            "id": self.id,
            "createdBy": self.created_by,
            "projectId": self.project_id,
            "createdAt": self.created_at.strftime(DATETIME_FORMAT),
            "searchedAt": self.searched_at.strftime(DATETIME_FORMAT) if self.searched_at is not None else None,
            "searchUrl": self.search_url,
            "active": self.active
        }

    @validates('id', 'created_by', 'project_id', 'created_at', 'searched_at', 'search_url', 'active')
    def _assert_active_project(self, key, value):
        if self.project and self.project.locked_at:
            raise ValidationError('Cannot change attributes of a search under a project ({}) that '
                                  'has been locked.'.format(self.project_id))

        return value


class SearchResultEntry(db.Model):
    __tablename__ = 'direct_award_search_result_entries'

    id = db.Column(db.Integer, primary_key=True)
    search_id = db.Column(db.Integer, db.ForeignKey('direct_award_searches.id'), index=True, nullable=False)
    archived_service_id = db.Column(db.Integer, db.ForeignKey('archived_services.id'), index=True, nullable=False)
