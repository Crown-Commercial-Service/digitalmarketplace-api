"""Add framework clarification_questions_open flag

Revision ID: 440
Revises: 430
Create Date: 2015-11-25 16:49:45.258601

"""

# revision identifiers, used by Alembic.
revision = '440'
down_revision = '430'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('frameworks', sa.Column('clarification_questions_open', sa.Boolean(), nullable=True))
    op.execute("""
        UPDATE frameworks SET clarification_questions_open = (CASE status
               WHEN 'open' THEN 't'
               ELSE 'f'
               END
              )::boolean
    """)
    op.alter_column('frameworks', 'clarification_questions_open', existing_type=sa.Boolean(), nullable=False)


def downgrade():
    op.drop_column('frameworks', 'clarification_questions_open')
