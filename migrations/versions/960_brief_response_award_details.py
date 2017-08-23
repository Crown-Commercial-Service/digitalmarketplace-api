"""award_details JSON blob and awarded_at date stamp on BriefResponse
Constraint on Brief to allow only one BriefResponse with non-null 'awarded_at'

Revision ID: 960
Revises: 950
Create Date: 2017-08-07 15:22:43.619680

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '960'
down_revision = '950'


def upgrade():
    op.add_column(
        'brief_responses',
        sa.Column('award_details', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}')
    )
    op.add_column('brief_responses', sa.Column('awarded_at', sa.DateTime(), nullable=True))
    op.create_index(
        'idx_brief_responses_unique_awarded_at_per_brief_id',
        'brief_responses',
        ['brief_id'],
        unique=True,
        postgresql_where=sa.text('awarded_at IS NOT NULL')
    )


def downgrade():
    op.drop_index('idx_brief_responses_unique_awarded_at_per_brief_id', table_name='brief_responses')
    op.drop_column('brief_responses', 'awarded_at')
    op.drop_column('brief_responses', 'award_details')
