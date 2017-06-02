"""Remove copied_from_brief_id column from briefs table as it has been superseded with 'is_a-copy' boolean column
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
import sqlalchemy as sa

briefs_table = sa.Table(
    'briefs',
    sa.MetaData(),
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('copied_from_brief_id', sa.Integer, nullable=False),
    sa.Column('is_a_copy', sa.Boolean, nullable=False),
)


def upgrade():
    """
    Migrate data from int column copied_from_brief_id to bool column is_a_copy then
    drop column as it has been superseded with 'is_a-copy' boolaean copy to fix a bug.
    """
    conn = op.get_bind()

    # UPDATE briefs
    # SET is_a_copy = true
    # WHERE copied_from_brief_id IS NOT null;
    query = briefs_table.update(
    ).where(
        briefs_table.c.copied_from_brief_id != sa.null()
    ).values(
        is_a_copy=sa.true()
    )
    conn.execute(query)

    # ALTER TABLE briefs DROP COLUMN copied_from_brief_id
    op.drop_column(
        'briefs',
        'copied_from_brief_id'
    )


def downgrade():
    """Reinstates copied_from_brief_id column, but without populating with data."""
    op.add_column(
        'briefs',
        sa.Column('copied_from_brief_id', sa.INTEGER, sa.ForeignKey('briefs.id'))
    )
