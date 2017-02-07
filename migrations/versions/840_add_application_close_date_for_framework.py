"""Add `application_close_date` for Framework
Revision ID: 840
Revises: 830
Create Date: 2017-02-06 11:09:26.852142
"""
from alembic import op
from datetime import datetime
import sqlalchemy as sa

from dmutils.formats import DATETIME_FORMAT, EUROPE_LONDON

# revision identifiers, used by Alembic.
revision = '840'
down_revision = '830'



def upgrade():
    op.add_column('frameworks', sa.Column('application_close_date', sa.DateTime(), nullable=True))
    op.add_column('frameworks', sa.Column('allow_declaration_reuse', sa.Boolean(), nullable=False, server_default='false'))

    for framework_slug, a_c_date, declaration_reuse in (
        ('digital-outcomes-and-specialists', datetime(2016, 1, 1, 15, tzinfo=EUROPE_LONDON), False),
        ('digital-outcomes-and-specialists-2', datetime(2017, 1, 16, 17, tzinfo=EUROPE_LONDON), True),
        ('g-cloud-8', datetime(2016, 6, 1, 17, tzinfo=EUROPE_LONDON), True),

    ):
        query_string = """UPDATE frameworks set application_close_date = '{a_c_date}'::DATE where slug = '{framework_slug}'"""
        op.execute(query_string.format(framework_slug=framework_slug, a_c_date=a_c_date.strftime(DATETIME_FORMAT)))

        query_string = """UPDATE frameworks set allow_declaration_reuse = '{declaration_reuse}'::BOOLEAN where slug = '{framework_slug}'"""
        op.execute(query_string.format(framework_slug=framework_slug, declaration_reuse=declaration_reuse))


def downgrade():
    op.drop_column('frameworks', 'allow_declaration_reuse')
    op.drop_column('frameworks', 'application_close_date')
