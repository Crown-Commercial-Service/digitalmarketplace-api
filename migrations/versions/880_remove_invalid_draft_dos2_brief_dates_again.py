"""Remove dates from draft dos2 briefs.
This is identical to the previous migration but will be run again to cover any draft briefs with invalid
dates that could have appeared during the previous API rollout process (after the previous migration but before
the code propogated fully to the ec2 instances).

Revision ID: 880
Revises: 870
Create Date: 2016-04-07

"""

# revision identifiers, used by Alembic.
revision = '880'
down_revision = '870'

from alembic import op
import sqlalchemy as sa


frameworks_table = sa.Table(
    'frameworks',
    sa.MetaData(),
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('slug', sa.String, nullable=False, unique=True, index=True)
)

briefs_table = sa.Table(
    'briefs',
    sa.MetaData(),
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('framework_id', sa.Integer, nullable=False),
    sa.Column('published_at', sa.DateTime, nullable=True),
    sa.Column('data', sa.JSON, nullable=True)
)


def upgrade():
    """Remove question and answer for startDate from briefs.data for draft dos2 briefs."""
    conn = op.get_bind()

    # SELECT id, data
    # FROM briefs JOIN frameworks ON briefs.framework_id = frameworks.id
    # WHERE frameworks.slug = 'digital-outcomes-and-specialists-2' AND briefs.published_at IS null;
    query = briefs_table.join(
        frameworks_table,
        briefs_table.c.framework_id == frameworks_table.c.id
    ).select(
        sa.and_(
            frameworks_table.c.slug == 'digital-outcomes-and-specialists-2',
            briefs_table.c.published_at == sa.null()
        )
    ).with_only_columns(
        briefs_table.c.id,
        briefs_table.c.data
    )
    results = conn.execute(query).fetchall()

    for brief_id, brief_data in results:
        if brief_data.pop('startDate', None) is not None:
            # UPDATE briefs SET data = _brief_data WHERE id = _brief_id;
            query = briefs_table.update().where(briefs_table.c.id==brief_id).values(data=brief_data)
            conn.execute(query)


def downgrade():
    pass
