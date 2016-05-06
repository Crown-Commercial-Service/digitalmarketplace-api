"""Change numberOfSuppliers to integer

Revision ID: 610
Revises: 600
Create Date: 2016-05-06 11:37:59.204714

"""

# revision identifiers, used by Alembic.
revision = '610'
down_revision = '600'

import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects import postgresql

briefs = table(
    'briefs',
    column('id', sa.Integer),
    column('data', postgresql.JSON),
)


def upgrade():
    conn = op.get_bind()
    for brief in conn.execute(briefs.select()):
        # Skip briefs with missing or integer 'numberOfSuppliers'
        if brief.data.get('numberOfSuppliers') is None or isinstance(brief.data['numberOfSuppliers'], int):
            continue

        # Get the last number in the 'numberOfSuppliers' string
        number_of_suppliers = re.search(r'(\d+)(?!.*\d)', brief.data['numberOfSuppliers'])
        if number_of_suppliers:
            brief.data['numberOfSuppliers'] = int(number_of_suppliers.group(0))
            conn.execute(
                briefs.update().where(
                    briefs.c.id == brief.id
                ).values(
                    data=brief.data
                )
            )


def downgrade():
    conn = op.get_bind()
    for brief in conn.execute(briefs.select()):
        # Skip briefs with missing or integer 'numberOfSuppliers'
        if brief.data.get('numberOfSuppliers') is None:
            continue

        brief.data['numberOfSuppliers'] = "{}".format(brief.data['numberOfSuppliers'])
        conn.execute(
            briefs.update().where(
                briefs.c.id == brief.id
            ).values(
                data=brief.data
            )
        )
