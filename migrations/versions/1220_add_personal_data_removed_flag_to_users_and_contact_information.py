"""Add 'obfuscated' flag to User and ContactInformation models

Revision ID: 1220
Revises: 1210
Create Date: 2018-05-01 09:47:36.085886

"""
from alembic import op
import sqlalchemy as sa


revision = '1220'
down_revision = '1210'


def upgrade():
    op.add_column('users', sa.Column('personal_data_removed', sa.Boolean(), nullable=False,  server_default=sa.false()))
    op.add_column(
        'contact_information',
        sa.Column('personal_data_removed', sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade():
    op.drop_column('contact_information', 'personal_data_removed')
    op.drop_column('users', 'personal_data_removed')

