"""Remove copied_from_brief_id column from briefs table  as it has been superseded with 'is_a-copy' boolaean column
to fix a bug. The bug made it impossible to delete a draft brief if a copy was made from it. Reason for this is
that the original and the copy were bound by a parent-child database relationship.

Revision ID: 910
Revises: 900
Create Date: 2017-06-01
"""

# revision identifiers, used by Alembic.
revision = '910'
down_revision = '900'

from alembic import op
from sqlalchemy import Column, ForeignKey, INTEGER


def upgrade():
    """Drop column as it has been superseded with 'is_a-copy' boolaean copy to fix a bug."""
    op.drop_column(
        'briefs',
        'copied_from_brief_id'
    )


def downgrade():
    """Reinstates copied_from_brief_id column, but without populating with data."""
    op.add_column(
        'briefs',
        Column('copied_from_brief_id', INTEGER, ForeignKey('briefs.id'))
    )
