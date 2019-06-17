"""tidy_up_latent

Tidy up a latent migration not previously picked up by alembic or ignored.

Revision ID: 1280
Revises: 1270
Create Date: 2019-06-10 15:51:48.661665

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1280'
down_revision = '1270'


def upgrade():
    # this field not has a "unique index" instead of a "unique constraint"
    op.drop_constraint('uq_direct_award_projects_external_id', 'direct_award_projects', type_='unique')


def downgrade():
    op.create_unique_constraint('uq_direct_award_projects_external_id', 'direct_award_projects', ['external_id'])
