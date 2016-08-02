"""Give published specialist briefs a requirementsLength of '2 weeks'

Revision ID: 690
Revises: 680
Create Date: 2016-07-28 12:30:11.406853

"""

# revision identifiers, used by Alembic.
revision = '690'
down_revision = '680'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects import postgresql

briefs = table(
    'briefs',
    column('id', sa.Integer),
    column('published_at', sa.DateTime),
    column('data', postgresql.JSON),
    column('lot_id', sa.Integer)
)


def upgrade():
    conn = op.get_bind()
    for brief in conn.execute(briefs.select()):
        # skip briefs that are unpublished (&) not a specialist brief (&) have requirements length set
        if not brief.published_at or brief.lot_id != 6 or brief.data.get('requirementsLength') != None:
            continue

        brief.data['requirementsLength'] = '2 weeks'
        conn.execute(
            briefs.update().where(
                briefs.c.id == brief.id
            ).values(
                data=brief.data
            )
        )


def downgrade():
    pass
