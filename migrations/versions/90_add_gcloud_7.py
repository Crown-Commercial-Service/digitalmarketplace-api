"""Add G-Cloud 7

Revision ID: 90_add_gcloud_7
Revises: 80_remove_framework_expired
Create Date: 2015-06-17 14:44:08.138355

"""

# revision identifiers, used by Alembic.
revision = '90_add_gcloud_7'
down_revision = '80_remove_framework_expired'

from alembic import op
from sqlalchemy.sql import table, column
from sqlalchemy import String


frameworks = table('frameworks',
    column('name', String),
    column('framework', String),
    column('status', String),
)


def upgrade():
    op.execute(
        frameworks.insert().
        values({'name': op.inline_literal('G-Cloud 7'),
                'framework': op.inline_literal('gcloud'),
                'status': op.inline_literal('pending')}))


def downgrade():
    op.execute(
        frameworks.delete().where(frameworks.c.name == 'G-Cloud 7'))
