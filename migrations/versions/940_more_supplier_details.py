""" Extend suppliers table with new fields (to be initially populated from declaration data)

Revision ID: 940
Revises: 930
Create Date: 2017-08-16 16:39:00.000000

"""

# revision identifiers, used by Alembic.
revision = '940'
down_revision = '930'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(u'suppliers', sa.Column('registered_name', sa.String(), nullable=True))
    op.add_column(u'suppliers', sa.Column('registration_country', sa.String(), nullable=True))
    op.add_column(u'suppliers', sa.Column('other_company_registration_number', sa.String(), nullable=True))
    op.add_column(u'suppliers', sa.Column('registration_date', sa.DateTime(), nullable=True))
    op.add_column(u'suppliers', sa.Column('vat_number', sa.String(), nullable=True))
    op.add_column(u'suppliers', sa.Column('organisation_size', sa.String(), nullable=True))
    op.add_column(u'suppliers', sa.Column('trading_status', sa.String(), nullable=True))


def downgrade():
    op.drop_column(u'suppliers', 'registered_name')
    op.drop_column(u'suppliers', 'registration_country')
    op.drop_column(u'suppliers', 'other_company_registration_number')
    op.drop_column(u'suppliers', 'registration_date')
    op.drop_column(u'suppliers', 'vat_number')
    op.drop_column(u'suppliers', 'organisation_size')
    op.drop_column(u'suppliers', 'trading_status')
