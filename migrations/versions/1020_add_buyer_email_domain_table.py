"""Add buyer email domain table

Revision ID: 1020
Revises: 1010
Create Date: 2017-10-10 15:18:22.683693

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1020'
down_revision = '1010'


def upgrade():
    op.create_table(
        'buyer_email_domains',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('domain_name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('buyer_email_domains_pkey'))
    )
    op.create_unique_constraint(
        op.f('uq_buyer_email_domains_domain_name'), 'buyer_email_domains', ['domain_name']
    )


def downgrade():
    op.drop_constraint(
        op.f('uq_buyer_email_domains_domain_name'), 'buyer_email_domains', type_='unique'
    )
    op.drop_table('buyer_email_domains')
