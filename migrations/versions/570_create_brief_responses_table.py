"""Create brief responses table

Revision ID: 570
Revises: 560
Create Date: 2016-02-10 12:19:22.888832

"""

# revision identifiers, used by Alembic.
revision = '570'
down_revision = '560'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('brief_responses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('data', postgresql.JSON(), nullable=False),
    sa.Column('brief_id', sa.Integer(), nullable=False),
    sa.Column('supplier_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['brief_id'], ['briefs.id'], ),
    sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.supplier_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_brief_responses_created_at'), 'brief_responses', ['created_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_brief_responses_created_at'), table_name='brief_responses')
    op.drop_table('brief_responses')
