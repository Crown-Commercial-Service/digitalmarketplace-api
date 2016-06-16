"""add framework_agreement_version to Framework

Revision ID: 640
Revises: 630
Create Date: 2016-06-16 11:37:21.802880

"""

# revision identifiers, used by Alembic.
revision = '640'
down_revision = '630'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('frameworks', sa.Column('framework_agreement_version', sa.String(), nullable=True))
    op.execute("""
        UPDATE frameworks SET framework_agreement_version = 'v1.0' WHERE slug = 'g-cloud-8'
    """)


def downgrade():
    op.drop_column('frameworks', 'framework_agreement_version')
