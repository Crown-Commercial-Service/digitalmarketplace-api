"""add data to work order

Revision ID: c6108e44a507
Revises: 750
Create Date: 2016-09-21 11:03:52.193666

"""

# revision identifiers, used by Alembic.
revision = '760'
down_revision = '750'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('work_order', sa.Column('data', postgresql.JSON(), nullable=False))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('work_order', 'data')
    ### end Alembic commands ###
