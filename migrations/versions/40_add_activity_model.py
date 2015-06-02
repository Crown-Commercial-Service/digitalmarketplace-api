"""

Revision ID: 40_add_activity_model
Revises: 30_add_versioning_to_suppliers
Create Date: 2015-05-29 14:41:40.006425

"""

# revision identifiers, used by Alembic.
revision = '40_add_activity_model'
down_revision = '30_add_versioning_to_suppliers'

from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('activity',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('verb', sa.Unicode(length=255), nullable=True),
    sa.Column('transaction_id', sa.BigInteger(), nullable=False),
    sa.Column('data', sqlalchemy_utils.types.json.JSONType(), nullable=True),
    sa.Column('object_type', sa.String(length=255), nullable=True),
    sa.Column('object_id', sa.BigInteger(), nullable=True),
    sa.Column('object_tx_id', sa.BigInteger(), nullable=True),
    sa.Column('target_type', sa.String(length=255), nullable=True),
    sa.Column('target_id', sa.BigInteger(), nullable=True),
    sa.Column('target_tx_id', sa.BigInteger(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activity_transaction_id'), 'activity', ['transaction_id'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_activity_transaction_id'), table_name='activity')
    op.drop_table('activity')
    ### end Alembic commands ###
