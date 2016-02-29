"""Add brief clarification questions

Revision ID: 580
Revises: 570
Create Date: 2016-02-23 16:53:28.171878

"""

# revision identifiers, used by Alembic.
revision = '580'
down_revision = '570'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('brief_clarification_questions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('brief_id', sa.Integer(), nullable=False),
    sa.Column('question', sa.String(), nullable=False),
    sa.Column('answer', sa.String(), nullable=False),
    sa.Column('published_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['brief_id'], ['briefs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_brief_clarification_questions_published_at'), 'brief_clarification_questions', ['published_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_brief_clarification_questions_published_at'), table_name='brief_clarification_questions')
    op.drop_table('brief_clarification_questions')
