"""Add new copied_from_brief_id column to briefs table to indicate where brief was cloned from.

Revision ID: 890
Revises: 880
Create Date: 2017-05-03
"""

# revision identifiers, used by Alembic.
revision = '890'
down_revision = '880'

from alembic import op
from sqlalchemy import Column, ForeignKey, INTEGER


def upgrade():
    """Add new copied_from_brief_id column to briefs table to indicate where brief was cloned from."""
    op.add_column(
        'briefs',
        Column('copied_from_brief_id', INTEGER, ForeignKey('briefs.id'))
    )


def downgrade():
    """Drop column."""
    op.drop_column(
        'briefs',
        'copied_from_brief_id'
    )
