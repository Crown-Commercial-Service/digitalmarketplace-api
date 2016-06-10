"""Remove mandatory assessment methods from briefs

Revision ID: 630
Revises: 620
Create Date: 2016-06-03 15:26:53.890401

"""

# revision identifiers, used by Alembic.
revision = '630'
down_revision = '620'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects import postgresql


briefs = table(
    'briefs',
    column('id', sa.Integer),
    column('lot_id', sa.Integer),
    column('data', postgresql.JSON),
)


def upgrade():
    conn = op.get_bind()
    for brief in conn.execute(briefs.select()):
        if brief.data.get('evaluationType') is None:
            continue

        optional_methods = list([
            method for method in brief.data['evaluationType']
            if method not in ['Work history', 'Written proposal']
        ])

        if brief.data['evaluationType'] != optional_methods:
            if optional_methods:
                brief.data['evaluationType'] = optional_methods
            else:
                brief.data.pop('evaluationType')

            conn.execute(briefs.update().where(briefs.c.id == brief.id).values(
                data=brief.data
            ))


def downgrade():
    conn = op.get_bind()
    for brief in conn.execute(briefs.select()):
        # Add written proposal to all outcomes and research participants briefs
        if brief.lot_id in [5, 8]:
            brief.data['evaluationType'] = ['Written proposal'] + brief.data.get('evaluationType', [])
        # Add work history to all specialists briefs
        elif brief.lot_id == 6:
            brief.data['evaluationType'] = ['Work history'] + brief.data.get('evaluationType', [])

        conn.execute(briefs.update().where(briefs.c.id == brief.id).values(
            data=brief.data
        ))
