"""Adds missing 'niceToHaveRequirements' to old published Brief data blobs.

Revision ID: 990
Revises: 980
Create Date: 2017-09-05 17:08:57.947569

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '990'
down_revision = '980'


briefs_table = sa.Table(
    'briefs',
    sa.MetaData(),
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('data', sa.JSON, nullable=True),
    sa.Column('published_at', sa.DateTime, nullable=True)
)


def upgrade():
    conn = op.get_bind()
    # SELECT id, data FROM briefs WHERE briefs.published_at IS NOT null
    query = briefs_table.select(
        briefs_table.c.published_at != sa.null()
    ).with_only_columns(
        briefs_table.c.id,
        briefs_table.c.data
    )
    results = conn.execute(query).fetchall()
    for brief_id, brief_data in results:
        if 'niceToHaveRequirements' not in brief_data:
            brief_data['niceToHaveRequirements'] = []
            # UPDATE briefs SET data = brief_data WHERE id = brief_id;
            query = briefs_table.update().where(briefs_table.c.id == brief_id).values(data=brief_data)
            conn.execute(query)


def downgrade():
    pass
