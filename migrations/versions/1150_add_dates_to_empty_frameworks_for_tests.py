"""Adds default (bad) framework lifecycle event datetimes where those fields are currently null, so that we can set them
as non-nullable in the next migration. This migration will run against preview/staging/production, but we have already
manually populated all of the frameworks there, so it will take no effect. The primary purpose of this migration is
to populate framework dates for API unit tests.

Revision ID: 1150
Revises: 1140
Create Date: 2018-05-08 09:53:43.699711

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column, and_


# revision identifiers, used by Alembic.
revision = '1150'
down_revision = '1140'


def upgrade():
    frameworks = table('frameworks',
                       column('applications_close_at_utc', sa.DateTime()),
                       column('clarifications_close_at_utc', sa.DateTime()),
                       column('clarifications_publish_at_utc', sa.DateTime()),
                       column('framework_expires_at_utc', sa.DateTime()),
                       column('framework_live_at_utc', sa.DateTime()),
                       column('intention_to_award_at_utc', sa.DateTime()))
    op.execute(
        frameworks.update().where(
            and_(
                frameworks.c.applications_close_at_utc == None,  # noqa
                frameworks.c.clarifications_close_at_utc == None,  # noqa
                frameworks.c.clarifications_publish_at_utc == None,  # noqa
                frameworks.c.framework_expires_at_utc == None,  # noqa
                frameworks.c.framework_live_at_utc == None,  # noqa
                frameworks.c.intention_to_award_at_utc == None,  # noqa
            )
        ).values(
            applications_close_at_utc='1970-01-01T00:00:00.000000Z',
            clarifications_close_at_utc='1970-01-01T00:00:00.000000Z',
            clarifications_publish_at_utc='1970-01-01T00:00:00.000000Z',
            framework_expires_at_utc='1970-01-01T00:00:00.000000Z',
            framework_live_at_utc='1970-01-01T00:00:00.000000Z',
            intention_to_award_at_utc='1970-01-01T00:00:00.000000Z',
        )
    )


def downgrade():
    pass
