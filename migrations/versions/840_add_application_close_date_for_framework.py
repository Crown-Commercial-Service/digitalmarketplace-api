"""Add `application_close_date` for Framework
Revision ID: 840
Revises: 830
Create Date: 2017-02-06 11:09:26.852142
"""
from alembic import op
from datetime import datetime
from dateutil import tz
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '840'
down_revision = '830'


frameworks_table = sa.table(
    'frameworks',
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('slug', sa.String, nullable=False, unique=True, index=True),
    sa.Column('allow_declaration_reuse', sa.Boolean),
    sa.Column('application_close_date', sa.DateTime)
)

tz_utc = tz.tzoffset('utc', 0)


def upgrade():
    op.add_column('frameworks', sa.Column('application_close_date', sa.DateTime(), nullable=True))
    op.add_column(
        'frameworks',
        sa.Column('allow_declaration_reuse', sa.Boolean(), nullable=False, server_default='false')
    )

    fields = ('slug', 'application_close_date', 'allow_declaration_reuse')
    new_values = (
        ('digital-outcomes-and-specialists', datetime(2016, 1, 1, 15, tzinfo=tz_utc), False),
        ('digital-outcomes-and-specialists-2', datetime(2017, 1, 16, 17, tzinfo=tz_utc), True),
        ('g-cloud-8', datetime(2016, 6, 1, 17, tzinfo=tz_utc), True),

    )
    new_values = [dict(zip(fields, i)) for i in new_values]
    for i in new_values:
        op.execute(
            frameworks_table.update().where(frameworks_table.c.slug==i.pop('slug')).values(**i)
        )


def downgrade():
    op.drop_column('frameworks', 'allow_declaration_reuse')
    op.drop_column('frameworks', 'application_close_date')
